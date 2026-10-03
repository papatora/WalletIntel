"""DEEP-CHECK 53 diamond candidates dari Cielo — verifikasi internal, jangan halu.

Metode (aproksimasi resmi, bukan verifier R1-R3 penuh):
  1. Tarik riwayat token transfer wallet di robin chain (Etherscan V2, max_pages).
  2. Side: to=wallet=BUY, from=wallet=SELL.
  3. Harga per event: price point TERDEKAT by block_num dari pool terlikuiditas
     token itu di DB lokal (6,86 jt titik). Token tanpa pool/price = UNPRICED
     (dilaporkan terbuka — TIDAK dihitung PnL-nya).
  4. FIFO round-trip per token → realized PnL; sisa holding = unrealized.
  5. Bandingkan dgn klaim GMGN; cek dev via created_tokens; catat label DB.

Output: results/cielo/deepcheck_summary.json + deepcheck_<addr>.json per wallet.
Metode & keterbatasan tertulis di setiap output — provenance terbuka.
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
import sys
import time
from bisect import bisect_left
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

OUT_DIR = REPO / "results" / "cielo"
DB = REPO / "data" / "topwallet.db"


class PriceCache:
    """(block, price) series per token, dari pool terlikuiditas, sorted by block."""

    def __init__(self):
        self.c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        self.series: dict[str, tuple[list[int], list[float]]] = {}
        self.best_pool: dict[str, str] = {}

    def _load(self, token: str) -> None:
        row = self.c.execute(
            "select address from pools where lower(token_address)=? "
            "order by coalesce(liquidity_usd,0) desc limit 1",
            (token.lower(),)).fetchone()
        if not row:
            self.series[token] = ([], [])
            return
        pool = row[0]
        self.best_pool[token] = pool
        pts = self.c.execute(
            "select block_num, price_usd from price_points where pool_address=? "
            "order by block_num", (pool,)).fetchall()
        blocks = [b for b, _ in pts]
        prices = [p for _, p in pts]
        self.series[token] = (blocks, prices)

    def price_at_block(self, token: str, block: int) -> float | None:
        if token not in self.series:
            self._load(token)
        blocks, prices = self.series.get(token, ([], []))
        if not blocks:
            return None
        i = bisect_left(blocks, block)
        cand = []
        if i < len(blocks):
            cand.append(abs(blocks[i] - block))
        if i > 0:
            cand.append(abs(blocks[i - 1] - block))
        j = min(range(len(cand)), key=lambda k: cand[k])
        idx = i if (len(cand) == 1 or j == 0) else i - 1
        # idx menunjuk blok terdekat
        if cand and min(cand) > 1_000_000:  # terlalu jauh — harga tak berlaku
            return None
        return prices[idx] if idx < len(prices) else None


def derive_wallet(transfers: list[dict], pc: PriceCache, wallet: str) -> dict:
    w = wallet.lower()
    tokens: dict[str, list] = {}
    unpriced = priced = 0
    for t in transfers:
        tok = ((t.get("token") or {}).get("address") or "").lower()
        if not tok:
            continue
        blk = int(t.get("block_number") or 0)
        raw = ((t.get("total") or {}).get("value")
               or t.get("value") or "0")
        try:
            amount = abs(int(raw)) / (10 ** int((t.get("token") or {}).get("decimals") or 18))
        except Exception:
            continue
        frm = ((t.get("from") or {}).get("hash") or "").lower()
        side = "SELL" if frm == w else "BUY"
        px = pc.price_at_block(tok, blk)
        if px is None:
            unpriced += 1
        else:
            priced += 1
        tokens.setdefault(tok, []).append((blk, side, amount, px))

    realized = unrealized = 0.0
    per_token = []
    for tok, evs in tokens.items():
        evs.sort()
        qty_out = 0.0
        cost_out = 0.0
        held_qty = 0.0
        cost_basis = 0.0
        realized_tok = 0.0
        buys = sells = 0
        for blk, side, amount, px in evs:
            if px is None:
                continue
            if side == "BUY":
                buys += 1
                held_qty += amount
                cost_basis += amount * px
            else:
                sells += 1
                if held_qty > 0:
                    avg = cost_basis / held_qty
                    sell_qty = min(amount, held_qty)
                    realized_tok += sell_qty * px - sell_qty * avg
                    held_qty -= sell_qty
                    cost_basis -= sell_qty * avg
                else:
                    # jual tanpa posisi tercatat (coverage bolong) — abaikan,
                    # terhitung ke arah KONSERVATIF (PnL kita低估)
                    pass
        last_px = next((px for (_, _, _, px) in reversed(evs) if px is not None), None)
        unrealized_tok = held_qty * last_px if (held_qty > 0 and last_px) else 0.0
        realized += realized_tok
        unrealized += unrealized_tok
        per_token.append({"token": tok, "buys": buys, "sells": sells,
                          "realized_usd": round(realized_tok, 2),
                          "unrealized_usd": round(unrealized_tok, 2),
                          "still_holding": held_qty > 0})
    per_token.sort(key=lambda x: x["realized_usd"], reverse=True)
    return {
        "realized_usd_est": round(realized, 2),
        "unrealized_usd_est": round(unrealized, 2),
        "events_priced": priced, "events_unpriced": unpriced,
        "n_tokens_touched": len(tokens),
        "tokens": per_token[:15],
        "method": "FIFO on transfers, price = nearest-block pool price dari DB lokal; "
                  "UNPRICED dikecualikan (konservatif)",
    }


async def main_async() -> int:
    from src.utils.etherscan_client import make_explorer_client
    from src.discover.gmgn_client import GmgnClient

    cands = json.loads((OUT_DIR / "diamond_candidates.json").read_text(encoding="utf-8"))
    ver = json.loads((OUT_DIR / "verify_results.json").read_text(encoding="utf-8"))["results"]
    pc = PriceCache()
    cli = make_explorer_client()
    gcli = GmgnClient()
    summary = []
    try:
        for i, c in enumerate(cands):
            a = c["address"]
            gmgn_claim = c.get("pnl_30d_usd_gmgn")
            rec = {
                "address": a, "gmgn_claim_30d": gmgn_claim,
                "labels_db": c.get("labels_db"),
                "lists": c.get("lists"),
            }
            try:
                transfers = await cli.address_token_transfers(a, max_pages=5)
                rec["n_transfers_fetched"] = len(transfers or [])
                d = derive_wallet(transfers or [], pc, a)
                rec.update(d)
                rec["ratio_est_vs_gmgn"] = (
                    round(d["realized_usd_est"] / gmgn_claim, 3)
                    if gmgn_claim and d["realized_usd_est"] > 0 else None)
            except Exception as e:
                rec["error"] = str(e)[:150]
            try:
                created = gcli.created_tokens("robinhood", a)
                rec["n_created_tokens"] = len(created or [])
            except Exception:
                rec["n_created_tokens"] = None
            verdict = "UNVERIFIABLE"
            if rec.get("n_created_tokens"):
                verdict = "DEV"
            elif rec.get("realized_usd_est") is not None:
                r = rec["realized_usd_est"]
                ratio = rec.get("ratio_est_vs_gmgn")
                if "INSIDER" in (c.get("labels_db") or []):
                    verdict = "INSIDER_FLAG_DB"
                elif ratio and ratio >= 0.5:
                    verdict = "CONFIRMED_BY_ESTIMATE"
                elif r > 0:
                    verdict = "POSITIVE_BUT_BELOW_CLAIM"
                else:
                    verdict = "NOT_CONFIRMED"
            rec["verdict"] = verdict
            summary.append(rec)
            (OUT_DIR / f"deepcheck_{a.lower()}.json").write_text(
                json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"[{i+1}/{len(cands)}] {a[:12]}... {verdict} "
                  f"est=${rec.get('realized_usd_est', 0):,.0f} "
                  f"vs gmgn=${gmgn_claim or 0:,.0f}", flush=True)
            time.sleep(0.4)
    finally:
        await cli.close()
        gcli.close()

    (OUT_DIR / "deepcheck_summary.json").write_text(
        json.dumps({"updated_at": datetime.now(timezone.utc).isoformat(),
                    "results": summary}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    from collections import Counter
    print("verdicts:", dict(Counter(r["verdict"] for r in summary)))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
