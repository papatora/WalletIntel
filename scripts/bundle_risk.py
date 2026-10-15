"""BUNDLE RISK INDEX (BRI) — port metode trench.bot ke Robinhood chain (S-54).

Sumber metode (di-review + di-reverse-engineer dari dokumentasi resmi mereka,
results/trench_docs/*.md — GitBook publik):
  - Bundle scanner : bundle = >=3 wallet unik beli di SLOT sama (Solana) —
    ekuivalen EVM: block sama. 2 wallet = zona false-positive (copy-trader).
  - Bundle Risk Index: 4 faktor berbobot — Funding 50%, Temporal 40%,
    Komposisi wallet 25%, Behavioral 20%; band 70-100 VERY HIGH / 40-69 HIGH /
    20-39 MEDIUM / 0-19 LOW. Red flag: >60% wallet baru, temporal rapat,
    funding stealth, top-20 holder >80% supply, wash (beli >100% supply,
    retensi <20%).
  - Rules user (telegram): 4 buy nempel di belakang dev = wallet mereka;
    cluster pegang 10%+ = skip; dev jual <1 menit = skip; top-10 holder >30%
    (ex pool/curve) = skip. 1 merah = skip.

Adaptasi ke data kita (compute-only, local DB — tanpa menyentuh VPS):
  - slot -> block_num (Robinhood ~0.1s/block: 60 dtk ~ 600 block)
  - funding origin -> INDUKAN/funder di wallet_labels.evidence (CLUSTER_MEMBER
    / RING_RECIPIENT) + known_entities utk tipe funder — LAPISAN yang
    bubblemaps miss (dokumentasi mereka mengakuinya sendiri)
  - komposisi wallet -> labels + wallets.first_seen (baru = <=2 hari dari
    token.first_seen)
  - supply -> eth_call totalSupply sekali per token (cache; kalau RPC gagal,
    konsentrasi dilaporkan relasi ter-track dengan flag coverage)
  - USD estimasi = harga snapshot token (bukan claim presisi)

Pemakaian:
  python scripts/bundle_risk.py <token_address>     # analisis 1 token
  python scripts/bundle_risk.py --scan              # batch: semua pump token playbook
Output: results/bundle_risk/<ca>.json + stdout verdict.
"""
from __future__ import annotations

import asyncio
import json
import statistics
import sqlite3
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

DB = REPO / "data" / "topwallet.db"
OUT = REPO / "results" / "bundle_risk"

BLOCK_SECONDS = 0.101          # Robinhood chain
EARLY_BLOCKS = 1800            # ~3 menit: jendela "early buyer"
BLOCK0_BLOCKS = 2              # "block 0" EVM: creation..+2
PACKED_BLOCKS = 30             # jito rule: 4 buy nempel di belakang dev
MIN_BUNDLE_WALLETS = 3         # <3 = false-positive zone (dok. trench)
BANDS = ((70, "VERY HIGH"), (40, "HIGH"), (20, "MEDIUM"), (0, "LOW"))


def _fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _ts_epoch(ts) -> float | None:
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        return float(ts)
    try:
        return datetime.fromisoformat(str(ts).replace(" ", "T")).timestamp()
    except ValueError:
        return None


_supply_cache: dict[str, int | None] = {}
_decimals_cache: dict[str, int | None] = {}


def _rpc_call(to: str, data: str) -> str | None:
    try:
        from src.utils.rpc_client import EvmRpcClient

        async def _call():
            c = EvmRpcClient()
            return await c.call("eth_call", [{"to": to, "data": data}, "latest"])

        r = asyncio.run(_call())
        return r if isinstance(r, str) else None
    except Exception:
        return None


def token_decimals(ca: str) -> int | None:
    """decimals(): DB dulu, lalu RPC (cache)."""
    if ca in _decimals_cache:
        return _decimals_cache[ca]
    out = None
    try:
        con0 = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        row = con0.execute("select decimals from tokens where lower(address)=?",
                           (ca,)).fetchone()
        con0.close()
        if row and row[0] is not None:
            out = int(row[0])
    except (sqlite3.Error, TypeError, ValueError):
        out = None
    if out is None:
        try:
            r = _rpc_call(ca, "0x313ce567")  # decimals()
            out = int(r, 16) if r else None
        except (TypeError, ValueError):
            out = None
    _decimals_cache[ca] = out
    return out


def total_supply(ca: str, decimals: int | None) -> int | None:
    """totalSupply via eth_call (1 call/token, cache). None = RPC gagal."""
    if ca in _supply_cache:
        return _supply_cache[ca]
    r = _rpc_call(ca, "0x18160ddd")  # totalSupply()
    out = int(r, 16) if r else None
    _supply_cache[ca] = out
    return out


def _labels_map(con: sqlite3.Connection) -> dict[str, list[str]]:
    m: dict[str, list[str]] = defaultdict(list)
    for a, l in con.execute("select lower(wallet_address), label from wallet_labels"):
        m[a].append(l)
    return m


def _funder_of(con: sqlite3.Connection, addr: str, labels: list[str]) -> tuple[str, str]:
    """Origin pendanaan wallet: (origin_addr, jenis). INDUKAN/cluster evidence
    = lapisan yang (menurut dokumentasi trench sendiri) dilewatkan bubblemaps."""
    for l in labels:
        if l.startswith("CLUSTER_MEMBER:"):
            cid = l.split(":", 1)[1]
            row = con.execute(
                "select evidence from wallet_labels where lower(wallet_address)=? "
                "and label like 'CLUSTER_MEMBER%' limit 1", (addr,)).fetchone()
            funder = None
            if row and row[0]:
                try:
                    e = json.loads(row[0])
                    funder = ((e.get(cid) or {}).get("funder")
                              or e.get("funder")) or None
                except (ValueError, TypeError):
                    funder = None
            return (funder or f"cluster:{cid}"), ("funder" if funder else "cluster")
        if l == "RING_RECIPIENT":
            return "ring", "ring"
    row = con.execute(
        "select evidence from wallet_labels where lower(wallet_address)=? "
        "and label='INSIDER' limit 1", (addr,)).fetchone()
    if row and row[0]:
        try:
            e = json.loads(row[0])
            senders = (e or {}).get("senders") or {}
            if senders:
                return ("insider:" + sorted(senders)[0][:20], "insider-sender")
        except (ValueError, TypeError):
            pass
    return ("", "")


def analyze(ca: str, con: sqlite3.Connection) -> dict:
    ca = ca.lower()
    tok = con.execute(
        "select symbol,name,decimals,price_usd,first_seen from tokens "
        "where lower(address)=?", (ca,)).fetchone()
    if tok is None:
        return {"ok": False, "error": "token tidak ada di DB lokal (jalankan delta dulu)"}
    symbol, name, decimals, snap_px, tok_first_seen = tok

    swaps = con.execute(
        """select lower(wallet_address), ts, block_num, side, token_amount
           from swap_events where lower(token_address)=? order by block_num, ts""",
        (ca,)).fetchall()
    if len(swaps) < 8:
        return {"ok": False, "error": f"swap terlalu sedikit ({len(swaps)}) — coverage kurang",
                "symbol": symbol}
    creation = swaps[0][2]
    n_traders = len({s[0] for s in swaps})

    if decimals is None:
        decimals = token_decimals(ca)
    supply = total_supply(ca, decimals)
    supply_flag = supply is not None and decimals is not None

    def pct(tok_amt: float) -> float | None:
        if supply and decimals is not None:
            try:
                return tok_amt / (10 ** int(decimals)) * 100.0
            except (TypeError, ValueError):
                return None
        return None

    # ---- 1. block-0 bundle + packed buys -----------------------------------
    by_block: dict[int, dict] = defaultdict(lambda: {"w": set(), "amt": 0.0})
    for wa, ts, blk, side, amt in swaps:
        if side == "BUY" and blk <= creation + PACKED_BLOCKS:
            by_block[blk]["w"].add(wa)
            by_block[blk]["amt"] += amt or 0.0
    block0_bundles = []
    for blk in sorted(by_block):
        if blk > creation + BLOCK0_BLOCKS:
            break
        d = by_block[blk]
        if len(d["w"]) >= MIN_BUNDLE_WALLETS:
            block0_bundles.append({"block": blk, "wallets": len(d["w"]),
                                   "supply_pct": pct(d["amt"]),
                                   "tokens": d["amt"]})
    packed = [{"block": blk, "wallets": len(d["w"]), "supply_pct": pct(d["amt"])}
              for blk, d in sorted(by_block.items())
              if len(d["w"]) >= 4 and creation < blk <= creation + PACKED_BLOCKS]

    # ---- 2. early buyers + funding/temporal/komposisi/behavioral ----------
    first_buy: dict[str, dict] = {}
    for wa, ts, blk, side, amt in swaps:
        if side != "BUY":
            continue
        e = first_buy.setdefault(wa, {"ts": _ts_epoch(ts), "blk": blk, "amt": amt or 0.0})
        if blk < e["blk"]:
            e.update(ts=_ts_epoch(ts), blk=blk, amt=amt or 0.0)
    early = {w: e for w, e in first_buy.items() if e["blk"] <= creation + EARLY_BLOCKS}
    labels = _labels_map(con)
    tfs = _ts_epoch(tok_first_seen) or (
        min((e["ts"] or 9e12) for e in early.values()) if early else None)

    fund_groups: dict[str, list[str]] = defaultdict(list)
    new_w = sn_w = 0
    for w in early:
        labs = labels.get(w, [])
        origin, kind = _funder_of(con, w, labs)
        if origin:
            fund_groups[origin].append(w)
        wrow = con.execute("select first_seen from wallets where lower(address)=?",
                           (w,)).fetchone()
        wfs = _ts_epoch(wrow[0]) if wrow and wrow[0] else None
        if wfs and tfs and (tfs - wfs) <= 2 * 86400:
            new_w += 1
        if any(l in labs for l in ("SNIPER", "BUNDLER_SUSPECT")):
            sn_w += 1

    n_early = max(len(early), 1)
    # funding cluster: origin berbagi >=3 wallet early
    clusters = []
    for origin, ws in sorted(fund_groups.items(), key=lambda kv: -len(kv[1])):
        if len(ws) < 3:
            continue
        tss = sorted(e["ts"] or 9e12 for e in (early[w] for w in ws))
        span_min = (tss[-1] - tss[0]) / 60.0 if tss[0] < 9e12 else None
        amts = [early[w]["amt"] for w in ws]
        cv = (statistics.pstdev(amts) / statistics.fmean(amts)) if amts and statistics.fmean(amts) else 1.0
        clusters.append({
            "origin": origin[:24], "wallets": len(ws),
            "supply_pct_bought": pct(sum(early[w]["amt"] for w in ws)),
            "first_trade_span_min": round(span_min, 2) if span_min is not None else None,
            "buy_amount_cv": round(cv, 3),
        })
        if len(clusters) >= 8:
            break
    # temporal keseluruhan: berapa % early buyer yang first-buy dalam window
    # 10 menit terpadat (sliding)
    tss = sorted((e["ts"] for e in early.values() if e["ts"]), )
    tight_share = tight_span = None
    if len(tss) >= 3:
        best_n, best_span = 0, None
        i = 0
        for j in range(len(tss)):
            while tss[j] - tss[i] > 600:
                i += 1
            if j - i + 1 > best_n:
                best_n, best_span = j - i + 1, (tss[j] - tss[i]) / 60.0
        tight_share = best_n / len(tss)
        tight_span = best_span

    new_pct = new_w / n_early
    sn_pct = sn_w / n_early

    # ---- 3. skor BRI (bobot trench) ---------------------------------------
    biggest_fund = max((len(ws) for ws in fund_groups.values()), default=0)
    big_fund_share = biggest_fund / n_early if biggest_fund >= 3 else 0.0
    funding_score = min(50.0, 50.0 * big_fund_share)
    temporal_score = min(40.0, 40.0 * (tight_share or 0.0)
                         + (12.0 if block0_bundles else 0.0))
    comp_score = min(25.0, 25.0 * (0.6 * new_pct + 0.4 * sn_pct))
    cv_main = clusters[0]["buy_amount_cv"] if clusters else None
    behav_score = min(20.0, 20.0 * (1 - min(cv_main, 0.5) / 0.5)) if cv_main is not None else 0.0
    bri = round(min(100.0, funding_score + temporal_score + comp_score + behav_score), 1)
    band = next(name for th, name in BANDS if bri >= th)

    # ---- 4. dev check -------------------------------------------------------
    dev = None
    if first_buy:
        dev = min(first_buy.items(), key=lambda kv: (kv[1]["blk"], kv[1]["ts"] or 0))[0]
    dev_swaps = [( _ts_epoch(ts), blk, side, amt) for wa, ts, blk, side, amt in swaps if wa == dev]
    dev_sold_1m = False
    if dev_swaps and first_buy.get(dev):
        t0 = first_buy[dev]["ts"]
        b0 = first_buy[dev]["blk"]
        dev_sold_1m = any(s == "SELL" and ((t or 9e12) - (t0 or 9e12)) <= 60
                          and blk - b0 <= 620 for t, blk, s, a in dev_swaps)
    dev_labels = labels.get(dev, []) if dev else []
    dev_is_labeled_dev = any(l == "DEV" or l.startswith("DEV_") for l in dev_labels)

    # ---- 5. konsentrasi holder (net posisi, ex pool) ------------------------
    net: dict[str, float] = defaultdict(float)
    for wa, ts, blk, side, amt in swaps:
        net[wa] += (amt or 0.0) if side == "BUY" else -(amt or 0.0)
    holders = sorted(((w, a) for w, a in net.items() if a > 0),
                     key=lambda kv: -kv[1])
    top10_pct = pct(sum(a for _, a in holders[:10])) if holders else None
    top20_pct = pct(sum(a for _, a in holders[:20])) if holders else None

    # ---- 6. red flags + verdict (rules telegram + BRI) ---------------------
    reds = []
    if block0_bundles and max(b["wallets"] for b in block0_bundles) >= 3:
        b0 = max(block0_bundles, key=lambda b: b["wallets"])
        reds.append(f"block-0 bundle: {b0['wallets']} wallet satu block"
                    + (f" pegang {b0['supply_pct']:.1f}% supply" if b0["supply_pct"] is not None else ""))
    for c in clusters:
        if (c["supply_pct_bought"] or 0) >= 10 and c["wallets"] >= 3:
            reds.append(f"funding cluster {c['origin']}: {c['wallets']} wallet "
                        f"beli {c['supply_pct_bought']:.1f}% supply")
            break
    if dev_sold_1m:
        reds.append("dev jual dalam 1 menit pertama")
    if top10_pct is not None and top10_pct > 30:
        reds.append(f"top-10 holder {top10_pct:.1f}% supply (>30%)")
    if top20_pct is not None and top20_pct > 80:
        reds.append(f"top-20 holder {top20_pct:.1f}% supply (>80%)")
    if packed and max(p["wallets"] for p in packed) >= 4:
        reds.append(f"packed buys: {max(p['wallets'] for p in packed)} wallet "
                    f"satu block di belakang launch")
    if new_pct > 0.6 and n_early >= 5 and (tight_share or 0) >= 0.5:
        # trench: red flag "wallet baru >60%" — tapi wallet muda saja over-flag
        # utk token yang baru launch (semua trader pasti muda). Dokumen mereka
        # menaruhnya bersebelahan dgn "Tight Temporal Clustering" — jadi butuh
        # keduanya: wallet baru DAN mayoritas first-buy dalam window 10 menit.
        reds.append(f"{new_pct*100:.0f}% early buyer = wallet baru (<=2 hari) "
                    f"+ {round((tight_share or 0)*100)}% first-buy <=10 menit")
    bri_band_i = 0 if bri >= 70 else (1 if bri >= 40 else None)
    if bri_band_i is not None:
        reds.append(f"BRI {bri} ({band}) — indikasi koordinasi")

    verdict = "SKIP" if reds else ("CAUTION" if bri >= 20 or (top10_pct or 0) > 20 else "PASS")

    return {
        "ok": True, "token": ca, "symbol": symbol,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "db_coverage": {"swaps": len(swaps), "traders": n_traders,
                        "early_buyers": n_early,
                        "supply_onchain": supply_flag,
                        "note": "konsentrasi hanya wallet ter-track; supply "
                                "on-chain = eth_call totalSupply"},
        "creation_block": creation,
        "block0_bundles": block0_bundles,
        "packed_buys": packed,
        "bri": {"score": bri, "band": band,
                "funding": round(funding_score, 1), "temporal": round(temporal_score, 1),
                "composition": round(comp_score, 1), "behavioral": round(behav_score, 1),
                "new_wallet_pct": round(new_pct * 100, 1),
                "sniper_pct": round(sn_pct * 100, 1),
                "tightest_10min_share": round(tight_share, 2) if tight_share is not None else None,
                "tightest_span_min": round(tight_span, 1) if tight_span is not None else None},
        "clusters": clusters,
        "dev": {"wallet": dev, "sold_within_1min": dev_sold_1m,
                "labeled_dev": dev_is_labeled_dev},
        "holders": {"top10_pct": round(top10_pct, 2) if top10_pct is not None else None,
                    "top20_pct": round(top20_pct, 2) if top20_pct is not None else None,
                    "tracked_holders": len(holders)},
        "red_flags": reds,
        "verdict": verdict,
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.execute("pragma busy_timeout=60000")
    if len(sys.argv) > 1 and sys.argv[1] not in ("--scan",):
        ca = sys.argv[1].strip().lower()
        if not ca.startswith("0x"):
            sys.exit("alamat harus 0x…")
        r = analyze(ca, con)
        (OUT / f"{ca}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
        print(json.dumps(r, ensure_ascii=False, indent=1)[:2600])
        return 0 if r.get("ok") else 1

    # --scan: semua pump token playbook
    pf = REPO / "results" / "playbook" / "pumps.json"
    pumps = json.loads(pf.read_text(encoding="utf-8"))
    rows = []
    for i, p in enumerate(pumps, 1):
        ca = p["token"]
        try:
            r = analyze(ca, con)
        except Exception as e:
            r = {"ok": False, "error": str(e)[:100], "token": ca}
        rows.append({"token": ca, "x": round(p.get("x", 0), 1),
                     "ok": r.get("ok"), "bri": (r.get("bri") or {}).get("score"),
                     "band": (r.get("bri") or {}).get("band"),
                     "verdict": r.get("verdict", r.get("error")),
                     "n_reds": len(r.get("red_flags") or [])})
        if i % 40 == 0:
            print(f"[scan] {i}/{len(pumps)}", flush=True)
    rows.sort(key=lambda r: -(r["bri"] or -1))
    (OUT / "scan.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                                   encoding="utf-8")
    n_red = sum(1 for r in rows if r["verdict"] == "SKIP")
    print(f"[scan] {len(rows)} pump token: {n_red} SKIP, "
          f"{sum(1 for r in rows if r['verdict'] == 'CAUTION')} CAUTION, "
          f"{sum(1 for r in rows if r['verdict'] == 'PASS')} PASS")
    for r in rows[:12]:
        print(f"  {r['token'][:12]}.. x={r['x']:>7.0f} BRI={r['bri']} {r['band']} "
              f"→ {r['verdict']} ({r['n_reds']} flag)")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
