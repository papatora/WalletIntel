"""STUDI KOHORT RUG PONS — validasi data-lokal atas pelajaran teman user (S-55).

Klaim yang diuji (research.txt + gambar, C:\\Users\\ROG\\Documents\\ClaudeCode\\
anotherresearchtoken):
  1. Dev Pons umumnya BELI 0.6-3 ETH saat launch, lalu exit.
  2. Kohort dev-buy 0.6-3 ETH  -> p80 rug saat ~4x mcap awal (TP 4x).
  3. Kohort dev-buy 3-3.5 ETH  -> p80 waktu-rug ~90 detik.
  4. Pola tangga: naik pelan lalu rug instan (verif Pons V1 = bisa jual).

Metode (data lokal kita, compute-only):
  - dev = wallet BUY pertama pada block launch; dev_buy_usd = derived
    (nearest-block price, metode dataset.py); dev_buy_eth = usd / harga WETH
    snapshot (APROKSIMASI — harga ETH historis tidak per-block di DB).
  - rug_onset = detik sejak launch sampai harga series jatuh <-80% dari
    puncak berjalan pasca-launch (nearest-block price_points).
  - max_x = kelipatan harga tertinggi sebelum rug onset (proxy mcap multiple;
    supply Pons umumnya fixed 1B).
  - IS/OOS: split by tanggal launch — 70% awal = IS, 30% akhir = OOS.

Output: results/pons_archetype/study.json + stdout.
Pemakaian: python scripts/pons_rug_archetype.py
"""
from __future__ import annotations

import json
import sqlite3
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DB = REPO / "data" / "topwallet.db"
OUT = REPO / "results" / "pons_archetype"

RUG_DROP = 0.80          # rug onset = harga jatuh >80% dari puncak berjalan
MIN_SWAPS = 12           # coverage minimum per token
COHORTS = [(0.6, 3.0, "0.6-3.0 ETH"), (3.0, 3.5, "3.0-3.5 ETH")]


def percentile(vals: list[float], p: float) -> float | None:
    if not vals:
        return None
    s = sorted(vals)
    k = max(0, min(len(s) - 1, int(round(p / 100 * (len(s) - 1)))))
    return s[k]


def main() -> int:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.execute("pragma busy_timeout=60000")

    weth = con.execute(
        "select price_usd from tokens where symbol in ('WETH','ETH') "
        "and price_usd is not null order by price_usd desc limit 1").fetchone()
    eth_px = weth[0] if weth else None
    if not eth_px:
        print("harga WETH tidak ada di DB")
        return 1

    tokens = con.execute(
        """select lower(address), symbol, first_seen from tokens
           where address in (select distinct token_address from swap_events
                             group by token_address
                             having count(*) >= ?)""",
        (MIN_SWAPS,)).fetchall()
    print(f"token kandidat (>= {MIN_SWAPS} swap): {len(tokens)}", flush=True)


    recs = []
    for i, (ca, sym, first_seen) in enumerate(tokens, 1):
        # token_address tersimpan lowercase di dump — pakai match exact agar
        # ix_swap_events_token_address terpakai (lower() = full scan)
        swaps = con.execute(
            """select wallet_address, block_num, side, token_amount
               from swap_events where token_address=?
               order by block_num, ts""", (ca,)).fetchall()
        if len(swaps) < MIN_SWAPS:
            continue
        creation_blk = swaps[0][1]
        dev = next((s for s in swaps if s[2] == "BUY"), None)
        if dev is None:
            continue
        dev_w, dev_blk, _, dev_amt = dev
        pools = [r[0] for r in con.execute(
            "select address from pools where token_address=?", (ca,)).fetchall()]
        if not pools:
            continue
        ph = ",".join("?" * len(pools))
        pts = [(r[0], r[1]) for r in con.execute(
            f"select block_num, price_usd from price_points "
            f"where pool_address in ({ph}) and price_usd > 0 "
            f"order by block_num", tuple(pools)).fetchall()]
        if len(pts) < 10:
            continue
        p0 = next((px for b, px in pts if b >= creation_blk), None)
        if not p0:
            continue
        dev_usd = dev_amt * p0
        dev_eth = dev_usd / eth_px
        peak, rug_t, max_x = 0.0, None, 0.0
        blocks = [b for b, _ in pts]
        for b, px in pts:
            if b < creation_blk:
                continue
            peak = max(peak, px)
            if peak > 0:
                max_x = max(max_x, px / p0)
            if rug_t is None and peak > 0 and px <= peak * (1 - RUG_DROP) and b > creation_blk:
                rug_t = (b - creation_blk) * 0.101
        if rug_t is None:
            rug_t = (blocks[-1] - creation_blk) * 0.101  # belum rug = disensor
        fs = None
        if first_seen:
            try:
                fs = datetime.fromisoformat(str(first_seen).replace(" ", "T")).timestamp()
            except ValueError:
                fs = None
        recs.append({"token": ca, "symbol": sym, "dev": dev_w,
                     "dev_eth": round(dev_eth, 3), "rug_s": round(rug_t, 1),
                     "max_x": round(max_x, 2), "launch_ts": fs,
                     "swaps": len(swaps)})
        if i % 300 == 0:
            print(f"  ...{i}/{len(tokens)}", flush=True)
    con.close()

    def cohort_stats(sel: list[dict]) -> dict:
        if not sel:
            return {"n": 0}
        rugs = [r["rug_s"] for r in sel]
        xs = [r["max_x"] for r in sel]
        return {"n": len(sel),
                "dev_eth_median": round(statistics.median([r["dev_eth"] for r in sel]), 3),
                "rug_p50_s": round(percentile(rugs, 50) or 0, 1),
                "rug_p80_s": round(percentile(rugs, 80) or 0, 1),
                "maxx_p50": round(percentile(xs, 50) or 0, 2),
                "maxx_p80": round(percentile(xs, 80) or 0, 2),
                "reach4x_pct": round(100 * sum(1 for x in xs if x >= 4) / len(xs), 1)}

    stamped = sorted((r for r in recs if r["launch_ts"]), key=lambda r: r["launch_ts"])
    cut = int(len(stamped) * 0.7)
    is_set, oos_set = stamped[:cut], stamped[cut:]
    oos_start = (datetime.fromtimestamp(oos_set[0]["launch_ts"], tz=timezone.utc)
                 .strftime("%Y-%m-%d")) if oos_set else "-"

    out = {"generated_at": datetime.now(timezone.utc).isoformat(),
           "eth_px_snapshot": eth_px,
           "tokens_studied": len(recs),
           "is_n": len(is_set), "oos_n": len(oos_set), "oos_start": oos_start,
           "all": {}, "oos": {}, "notes": [
               "dev_buy_eth = aproksimasi (usd derived / WETH snapshot)",
               "rug_onset = harga <-80% dari puncak berjalan post-launch; "
               "belum-rug = disensor di akhir data",
               "max_x = kelipatan harga (proxy mcap; supply Pons umumnya fixed)"]}

    for lo, hi, name in COHORTS:
        out["all"][name] = cohort_stats([r for r in recs if lo <= r["dev_eth"] <= hi])
        out["oos"][name] = cohort_stats([r for r in oos_set if lo <= r["dev_eth"] <= hi])
    out["all"]["di_luar_kohort"] = cohort_stats(
        [r for r in recs if not any(lo <= r["dev_eth"] <= hi for lo, hi, _ in COHORTS)])

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "study.json").write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                    encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1)[:2800])
    return 0


if __name__ == "__main__":
    sys.exit(main())
