"""S-51k/S-52 — menguji playbook "How I Find Smart Wallets Before They Find The
Next Runner" (input user 2026-10-06) TERHADAP DATA LOKAL KITA.

Terjemahan playbook -> pengujian terukur:
  P1 "start with a coin that went crazy"
     -> token dgn puncak kenaikan harga >= 20x dari series price_points lokal.
  P2 "pull the first 20 buyers"
     -> swap_events: wallet dgn BUY TERAWAL di token tsb; rank pembeli dicatat.
  P3 "ignore bots / dead wallets"
     -> buang label MEV_BOT/BOT/SNIPER_BOT/POOL_CONTRACT/NOISE; buang wallet
        tanpa aktivitas > IDLE_DAYS terakhir.
  P4 "same low cap in 3 different smart wallets"
     -> SMART = wallet yang early (beli sebelum puncak) di >=2 pump berbeda
        DAN net flow positif. Token dgn >=3 SMART buyers = SINYAL.
  P5 "$100K vs $1K beda permainan"
     -> net-flow wallet dipisah per tier.

NET-FLOW = DERIVED PRICING (usd_value di dump VPS 100% NULL — jangan dibaca).
Metode = port dari "Database Local only/html/dataset.py" (sumber baku):
  usd = token_amount x harga price_points nearest-block at-or-before swap
  (fallback titik pertama sesudahnya), outlier guard usd > liquidity token.
  SATU KOREKSI thd dataset.py: kalibrasi skala hanya bila rasio
  titik-terakhir vs snapshot >= 1000x (signature bug skala 1e-12 era USDG) —
  rule-30x dataset.py ternyata salah tembak pada token yang harganya memang
  bergerak pasca-titik-terakhir (kasus BLAST 0x724a163f: rescale 37,58x
  menggelembungkan net wallet $3,6K -> $135K). Temuan utk dataset.py
  dilaporkan di PRE_COMPACT S-52 — belum diubah di explorer.

Output: results/playbook/smart_confluence.json + pumps.json (semua pump) +
laporan stdout. Semua dari data lokal — bukan klaim.

Pemakaian: python scripts/playbook_smart_confluence.py [path_db_opsional]
"""
from __future__ import annotations

import bisect
import json
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DB = REPO / "data" / "topwallet.db"
OUT = REPO / "results" / "playbook"
MIN_PUMP_X = 20.0        # "went crazy": >=20x dari bottom ke top
MIN_SMART_BUYERS = 3     # playbook: same low cap in 3 different smart wallets
MIN_EARLY_PUMPS = 2      # SMART: early di >=2 pump berbeda
IDLE_DAYS = 30           # P3: wallet tanpa aktivitas >30 hari = dead
CALIBRATE_RATIO = 1000.0 # rescale series hanya bila last/snapshot >=1000x (bug skala)
BOT_LABELS = ("MEV_BOT", "BOT", "SNIPER_BOT", "POOL_CONTRACT", "NOISE")


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def build_pricing(conn: sqlite3.Connection):
    """Port dataset.py DENGAN SATU KOREKSI (temuan S-52, terbukti di BLAST
    0x724a163f): kalibrasi 30x dataset.py me-rescale SELURUH histori harga
    saat titik terakhir series >30x dari harga snapshot — padahal itu bisa
    sekadar harga yang bergerak (token pump/dump SETELAH titik terakhir),
    bukan bug skala. Untuk net-flow historis, rescale seperti itu menggelembung-
    kan/empeskan harga blok lama (contoh terukur: BLAST terkalibrasi 37,58x,
    net wallet top berubah $3,6K -> $135K palsu). Bug skala asli (era USDG
    1e-12) signature-nya EKSTREM — jadi rescale hanya bila rasio >=1000x.
    (dataset.py explorer sendiri masih pola 30x — temuan dilaporkan, jangan
    diubah diam-diam; lihat PRE_COMPACT S-52.)"""
    snap: dict[str, float] = {}
    liquidity: dict[str, float] = {}
    for addr, px, liq in conn.execute(
            "select lower(address), price_usd, liquidity_usd from tokens"):
        if px:
            snap[addr] = float(px)
        if liq:
            liquidity[addr] = float(liq)

    pool_for: dict[str, str] = {}
    for tok, pool, n in conn.execute(
        "select lower(p.token_address), p.address, count(pp.id) from pools p "
        "left join price_points pp on pp.pool_address=p.address group by p.address order by 3"
    ):
        pool_for[tok] = pool  # asc -> last write = pool dgn terbanyak titik

    series: dict[str, tuple[list[int], list[float]]] = {}
    calibrated = 0
    would_calibrate_30x = 0
    for tok, pool in pool_for.items():
        rows = [r for r in conn.execute(
            "select block_num, price_usd from price_points "
            "where pool_address=? order by block_num", (pool,)).fetchall() if r[1]]
        if not rows:
            continue
        scale = 1.0
        snap_px = snap.get(tok)
        last = rows[-1][1]
        if snap_px:
            ratio = last / snap_px
            if not (1 / 30 <= ratio <= 30):
                would_calibrate_30x += 1
            if not (1 / CALIBRATE_RATIO <= ratio <= CALIBRATE_RATIO):
                scale = snap_px / last  # signature bug skala (>=1000x) -> rescale
                calibrated += 1
        series[tok] = ([r[0] for r in rows], [r[1] * scale for r in rows])

    def price_at(tok: str, block: int):
        s = series.get(tok)
        if not s:
            return None
        j = bisect.bisect_right(s[0], block) - 1
        return s[1][j] if j >= 0 else s[1][0]  # fallback: titik pertama sesudah

    return series, snap, liquidity, price_at, calibrated, would_calibrate_30x


def main() -> int:
    db = Path(sys.argv[1]) if len(sys.argv) > 1 else DB
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
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
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "pumps.json").write_text(json.dumps(
        sorted(pumps.values(), key=lambda d: -d["x"]),
        ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- 2. first-buyers per token pump (+ rank pembeli) -----------------
    pump_tokens = set(pumps)
    buyers: dict[str, list] = defaultdict(list)
    q = ("select lower(wallet_address), token_address, min(block_num), "
         "count(*) from swap_events where lower(token_address) in ("
         + ",".join("?" * len(pump_tokens)) + ") group by 1,2")
    for wa, tok, first_blk, n in conn.execute(q, tuple(pump_tokens)):
        buyers[tok].append((wa, first_blk, n))
    buyer_rank: dict[tuple, int] = {}  # (tok, wa) -> urutan first-buy di token itu
    for tok, lst in buyers.items():
        for rank, (wa, _, _) in enumerate(sorted(lst, key=lambda t: t[1]), 1):
            buyer_rank[(tok, wa)] = rank

    # ---- 3. wallet "early": beli sebelum puncak di >=2 pump --------------
    early: dict[str, set] = defaultdict(set)
    for tok, meta in pumps.items():
        top_b = meta.get("top_block")
        if not top_b:
            continue
        for wa, first_blk, _ in buyers.get(tok, []):
            if first_blk <= top_b:
                early[wa].add(tok)

    # ---- 4. NET-FLOW derived pricing (port dataset.py) --------------------
    print("membangun series harga derived...", flush=True)
    series, snap, liquidity, price_at, n_calibrated, n_would_30x = build_pricing(conn)
    print(f"series token: {len(series)} | kalibrasi skala (>= {CALIBRATE_RATIO:.0f}x): "
          f"{n_calibrated} | yang akan di-rescale rule-30x dataset.py: {n_would_30x}", flush=True)

    pump_set = pump_tokens
    net_all: dict[str, float] = defaultdict(float)
    net_pump: dict[str, float] = defaultdict(float)
    buy_all: dict[str, float] = defaultdict(float)
    last_ts: dict[str, str] = {}
    prov = {"priced_series": 0, "priced_fallback": 0, "unpriced": 0, "outlier": 0}
    prov_pump = {"priced": 0, "unpriced": 0}
    for wa, ta, ts, block, side, amt in conn.execute(
            "select lower(wallet_address), lower(token_address), ts, block_num, "
            "side, token_amount from swap_events order by ts"):
        if ts > last_ts.get(wa, ""):
            last_ts[wa] = ts
        is_pump = ta in pump_set
        p = price_at(ta, block)
        from_fallback = p is None
        if from_fallback:
            p = snap.get(ta)
        usd = round(amt * p, 2) if (p is not None and amt is not None) else -1
        if usd > (liquidity.get(ta) or 1_000_000):  # lebih besar dari seluruh pool = harga rusak
            usd = -1
            prov["outlier"] += 1
        if usd < 0:
            prov["unpriced"] += 1
            if is_pump:
                prov_pump["unpriced"] += 1
        else:
            prov["priced_fallback" if from_fallback else "priced_series"] += 1
            if is_pump:
                prov_pump["priced"] += 1
            sgn = 1.0 if side == "SELL" else -1.0
            net_all[wa] += sgn * usd
            if is_pump:
                net_pump[wa] += sgn * usd
            if side == "BUY":
                buy_all[wa] += usd

    # ---- 5. label + filter playbook (bot / dead) --------------------------
    labels: dict[str, list] = {}
    for a, lab in conn.execute(
            "select lower(wallet_address), label from wallet_labels"):
        labels.setdefault(a, []).append(lab)

    db_max_ts = conn.execute("select max(ts) from swap_events").fetchone()[0]
    cutoff = (datetime.strptime(db_max_ts[:19], "%Y-%m-%d %H:%M:%S")
              - timedelta(days=IDLE_DAYS)).strftime("%Y-%m-%d %H:%M:%S")

    smart: dict[str, dict] = {}
    n_dead = n_bot = 0
    for wa, toks in early.items():
        if len(toks) < MIN_EARLY_PUMPS:
            continue
        labs = labels.get(wa, [])
        bots = [b for b in BOT_LABELS if b in labs]
        if bots:
            n_bot += 1
            continue  # P3: ignore bots
        if last_ts.get(wa, "") < cutoff:
            n_dead += 1
            continue  # P3: ignore dead (>30 hari tanpa aktivitas)
        first20 = sum(1 for t in toks if buyer_rank.get((t, wa), 10**9) <= 20)
        smart[wa] = {
            "n_early_pumps": len(toks),
            "net_all_usd": round(net_all.get(wa, 0.0), 2),
            "net_pump_usd": round(net_pump.get(wa, 0.0), 2),
            "buy_all_usd": round(buy_all.get(wa, 0.0), 2),
            "first20_buys": first20,
            "labels": labs,
            "last_active": last_ts.get(wa),
        }

    # SMART final = net flow positif (seluruh aktivitas wallet, harga derived)
    smart_pos = {w: v for w, v in smart.items() if v["net_all_usd"] > 0}

    # Subset "bersih": tanpa label yang bisa menjelaskan net positif tanpa
    # skill (insider/airdrop/dev/sniper/bundler) — kandidat copytrade inti.
    DIRTY = {"INSIDER", "AIRDROP_FARMER", "PHISHING_TARGET", "DEV",
             "DEV_SERIAL_RUGGER", "SNIPER", "BUNDLER", "MEV_BOT", "BOT",
             "SNIPER_BOT", "WHALE_SUS", "CLUSTER_MEMBER"}
    for w, v in smart_pos.items():
        v["clean"] = not any(l in DIRTY for l in v["labels"])

    # ---- 6. tier P5: $100K vs $1K beda permainan --------------------------
    def tier(v: float) -> str:
        if v >= 100_000:
            return ">=100K"
        if v >= 10_000:
            return "10K-100K"
        if v >= 1_000:
            return "1K-10K"
        return "<1K"

    tiers: dict[str, int] = defaultdict(int)
    for v in smart_pos.values():
        tiers[tier(v["net_all_usd"])] += 1

    # ---- 7. confluence: token dgn >=3 SMART early buyers ------------------
    token_smart: dict[str, list] = defaultdict(list)
    token_clean: dict[str, list] = defaultdict(list)
    for wa, v in smart_pos.items():
        for t in early[wa]:
            token_smart[t].append(wa)
            if v["clean"]:
                token_clean[t].append(wa)
    signals = []
    for t, ws in token_smart.items():
        if len(ws) >= MIN_SMART_BUYERS:
            meta = pumps.get(t, {})
            signals.append({
                "token": t, "smart_wallets": len(ws), "wallets": ws,
                "clean_wallets": token_clean.get(t, []),
                "pump_x": round(meta.get("x", 0), 1),
                "note": "same low cap bought early by >=3 smart wallets",
            })
    signals.sort(key=lambda s: (-len(s["clean_wallets"]), -s["smart_wallets"]))

    top_smart = sorted(smart_pos.items(), key=lambda kv: -kv[1]["net_all_usd"])[:50]
    top_clean = sorted(((w, v) for w, v in smart_pos.items() if v["clean"]),
                       key=lambda kv: -kv[1]["net_all_usd"])[:50]
    clean_pos = sum(1 for v in smart_pos.values() if v["clean"])
    confluence_clean = sum(1 for s in signals if len(s["clean_wallets"]) >= MIN_SMART_BUYERS)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "db": str(db),
        "db_max_ts": db_max_ts,
        "pump_tokens": len(pumps),
        "early_wallets_ge1": len(early),
        "early_ge2_before_filters": sum(1 for t in early.values() if len(t) >= MIN_EARLY_PUMPS),
        "excluded_bot": n_bot,
        "excluded_dead_gt30d": n_dead,
        "smart_wallets": len(smart_pos),
        "smart_clean_wallets": clean_pos,
        "smart_tiers": dict(sorted(tiers.items())),
        "smart_first20_any": sum(1 for v in smart_pos.values() if v["first20_buys"] > 0),
        "confluence_tokens": len(signals),
        "confluence_tokens_clean": confluence_clean,
        "pricing_provenance": {"all_swaps": prov, "pump_swaps": prov_pump,
                               "series_tokens": len(series),
                               "calibrated_series_ge1000x": n_calibrated,
                               "series_dataset30x_would_rescale": n_would_30x,
                               "calibrate_policy": f"rescale hanya rasio >= {CALIBRATE_RATIO:.0f}x (bug skala); harga historis dari series mentah — lihat temuan BLAST 0x724a163f"},
        "top_smart_wallets": [
            {"wallet": w, **v} for w, v in top_smart],
        "top_clean_wallets": [
            {"wallet": w, **v} for w, v in top_clean],
        "signals": signals[:30],
    }
    (OUT / "smart_confluence.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    print("", flush=True)
    print(f"early >=1 pump : {len(early)}", flush=True)
    print(f"early >=2 pump : {report['early_ge2_before_filters']} (sebelum filter)", flush=True)
    print(f"  dibuang bot  : {n_bot}", flush=True)
    print(f"  dibuang dead : {n_dead} (idle >{IDLE_DAYS} hari)", flush=True)
    print(f"SMART (net>0)  : {len(smart_pos)} (bersih: {clean_pos})", flush=True)
    print(f"tier net       : {dict(sorted(tiers.items()))}", flush=True)
    print(f"confluence tok : {len(signals)}", flush=True)
    print(f"provenance     : {prov}", flush=True)
    print(f"kalibrasi      : {n_calibrated} series >= {CALIBRATE_RATIO:.0f}x | rule-30x dataset.py akan menyentuh {n_would_30x} series", flush=True)
    print(f"                 pump-scope: {prov_pump}", flush=True)
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
