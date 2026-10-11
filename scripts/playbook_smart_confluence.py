"""S-51k — menguji playbook "How I Find Smart Wallets Before They Find The
Next Runner" (input user 2026-10-06) TERHADAP DATA LOKAL KITA.

Terjemahan playbook -> pengujian terukur:
  P1 "start with a coin that went crazy"
     -> token dgn puncak kenaikan harga >= 20x dari series price_points lokal.
  P2 "pull the first 20 buyers"
     -> swap_events: wallet dgn BUY TERAWAL di token tsb (20 teratas per token).
  P3 "ignore bots / dead wallets"
     -> buang label MEV_BOT/BOT/SNIPER_BOT; buang wallet tanpa aktivitas >30 hari.
  P4 "same low cap in 3 different smart wallets"
     -> SMART = wallet yang early (beli sebelum puncak) di >=2 pump berbeda
        DAN net flow positif. Token dgn >=3 SMART buyers = SINYAL.

Output: results/playbook/smart_confluence.json + laporan stdout.
Semua dari data lokal (price_points 7,2 jt + swap_events 1,2 jt) — bukan klaim.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DB = REPO / "data" / "topwallet.db"
OUT = REPO / "results" / "playbook"
MIN_PUMP_X = 20.0        # "went crazy": >=20x dari bottom ke top
MIN_SMART_BUYERS = 3     # playbook: same low cap in 3 different smart wallets
MAX_HOLD_DAYS = 400
BOT_LABELS = ("MEV_BOT", "BOT", "SNIPER_BOT", "POOL_CONTRACT", "NOISE")


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main() -> int:
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.execute("pragma busy_timeout=60000")

    # ---- 1. temukan token "went crazy" dari price_points -----------------
    print("mencari token pump >=20x dari price_points...", flush=True)
    pumps: dict[str, dict] = {}
    pool_count = 0
    for pool, in conn.execute("select address from pools"):
        pool_count += 1
        pts = conn.execute(
            "select block_num, price_usd from price_points "
            "where pool_address=? order by block_num", (pool,)).fetchall()
        if len(pts) < 10:
            continue
        prices = [(b, p) for b, p in pts if p and p > 0]
        if not prices:
            continue
        lo_b, lo_p = min(prices, key=lambda x: x[1])
        after = [(b, p) for b, p in prices if b >= lo_b]
        hi_b, hi_p = max(after, key=lambda x: x[1])
        if lo_p <= 0 or hi_b is None:
            continue
        x = hi_p / lo_p
        if x < MIN_PUMP_X:
            continue
        tokrow = conn.execute("select token_address from pools where address=?",
                              (pool,)).fetchone()
        if not tokrow:
            continue
        tok = tokrow[0].lower()
        prev = pumps.get(tok)
        if prev is None or x > prev["x"]:
            pumps[tok] = {"token": tok, "pool": pool, "x": x,
                          "bottom_block": lo_b, "top_block": hi_b,
                          "bottom_price": lo_p, "top_price": hi_p,
                          "n_points": len(prices)}
    print(f"pool dipindai: {pool_count}", flush=True)
    print(f"token pump >=20x: {len(pumps)}", flush=True)
    if not pumps:
        print("tidak ada pump >=20x — turunkan MIN_PUMP_X")
        return 0
    OUT = Path(REPO / "results" / "playbook")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "pumps.json").write_text(json.dumps(
        sorted(pumps.values(), key=lambda d: -d["x"])[:100],
        ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- 2. first-buyers per token pump ----------------------------------
    pump_tokens = set(pumps)
    buyers: dict[str, list] = defaultdict(list)
    q = ("select lower(wallet_address), token_address, min(block_num), "
         "count(*) from swap_events where lower(token_address) in ("
         + ",".join("?" * len(pump_tokens)) + ") group by 1,2")
    for wa, tok, first_blk, n in conn.execute(q, tuple(pump_tokens)):
        buyers[tok].append((wa, first_blk, n))

    # ---- 3. wallet "smart": early (sebelum puncak) di >=2 pump + profit ---
    early: dict[str, set] = defaultdict(set)
    for tok, meta in pumps.items():
        top_b = meta.get("top_block")
        if not top_b:
            continue
        for wa, first_blk, _ in buyers.get(tok, []):
            if first_blk <= top_b:
                early[wa].add(tok)

    # net flow per wallet (semua token, dari DB) utk filter "profit"
    net: dict[str, float] = {}
    for wa, usd, side in conn.execute(
            "select lower(wallet_address), usd_value, side from swap_events"):
        if usd is None:
            continue
        net[wa] = net.get(wa, 0) + (usd if side == "SELL" else -usd)

    smart = {}
    for wa, toks in early.items():
        if len(toks) >= 2 and net.get(wa, 0) > 0:
            smart[wa] = {"n_early_pumps": len(toks), "net_usd": round(net[wa], 2)}
    print(f"SMART wallets (early >=2 pump, net>0): {len(smart)}", flush=True)

    # ---- 4. confluence: token dgn >=3 SMART early buyers ------------------
    token_smart: dict[str, list] = defaultdict(list)
    for wa, toks in early.items():
        if wa not in smart:
            continue
        for t in toks:
            token_smart[t].append(wa)
    signals = []
    for t, ws in token_smart.items():
        if len(ws) >= MIN_SMART_BUYERS:
            meta = pumps.get(t, {})
            signals.append({
                "token": t, "smart_wallets": len(ws), "wallets": ws,
                "pump_x": round(meta.get("x", 0), 1),
                "note": "same low cap bought early by >=3 smart wallets",
            })
    signals.sort(key=lambda s: -s["smart_wallets"])

    # ---- 5. kredensial wallet SMART: bot? inactive? -----------------------
    labels = {}
    for a, lab in conn.execute(
            "select lower(wallet_address), label from wallet_labels"):
        labels.setdefault(a, []).append(lab)
    for wa in list(smart):
        labs = labels.get(wa, [])
        bots = [b for b in BOT_LABELS if b in labs]
        if bots:
            smart[wa]["bot_labels"] = bots
    n_bot = sum(1 for v in smart.values() if v.get("bot_labels"))

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pump_tokens": len(pumps),
        "smart_wallets": len(smart),
        "smart_with_bot_labels": n_bot,
        "confluence_tokens": len(signals),
        "signals": signals[:30],
    }
    (OUT / "smart_confluence.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"SMART: {len(smart)} | confluence tokens: {len(signals)}", flush=True)
    print("SMART dgn bot label:", n_bot, flush=True)
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
