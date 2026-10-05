"""Rapikan GENERALIST (mandat user 2026-10-05): GENERALIST = label UNTUK wallet
yang TIDAK punya label lain. Wallet multi-label tidak boleh membawa GENERALIST.

S-51 tambahan: pecah GENERALIST besar jadi bucket yang lebih bermakna & rapi:
  - DORMANT  : swap 1-2 dan tidak aktif >= 30 hari (blok) — bukan NOISE (bukan
               tepat 1 swap / masih ada tx), hanya tidur.
  - ACTIVE_MIN : swap >= 3 dan aktif <= 30 hari, tanpa label khusus — trader
               aktif kecil yang belum lolos klasifikasi.
Semua idempoten. Jalankan SETELAH night_delta.

Pemakaian: python scripts/dedupe_generalist.py
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DB = REPO / "data" / "topwallet.db"
IDLE_DAYS = 30
BLOCKS_PER_DAY = 864_000


def main() -> int:
    conn = sqlite3.connect(DB, timeout=60)
    conn.execute("pragma busy_timeout=60000")
    now = datetime.now(timezone.utc).isoformat()

    # ---- 1. buang GENERALIST dari wallet multi-label --------------------
    multi = [r[0] for r in conn.execute("""
        select wallet_address from wallet_labels
        group by wallet_address
        having count(distinct label) > 1
           and sum(case when label='GENERALIST' then 1 else 0 end) > 0
    """)]
    conn.executemany(
        "delete from wallet_labels where wallet_address=? and label='GENERALIST'",
        [(a,) for a in multi])
    print(f"GENERALIST duplikat dihapus: {len(multi)} wallet")

    # S-51h (audit): bucket sisa (ACTIVE_MIN/DORMANT) juga TIDAK BOLEH menempel
    # di wallet yang punya label khusus (21 kasus CT+ACTIVE_MIN ditemukan audit).
    for bucket in ("ACTIVE_MIN", "DORMANT"):
        multi2 = [r[0] for r in conn.execute("""
            select wallet_address from wallet_labels
            group by wallet_address
            having sum(case when label = ? then 1 else 0 end) > 0
               and sum(case when label not in (?, 'GENERALIST') then 1 else 0 end) > 0
        """, (bucket, bucket))]
        conn.executemany(
            "delete from wallet_labels where wallet_address=? and label=?",
            [(a, bucket) for a in multi2])
        if multi2:
            print(f"{bucket} duplikat dgn label khusus dihapus: {len(multi2)}")

    # ---- 2. bucket GENERALIST: DORMANT / ACTIVE_MIN ---------------------
    cur_block = 80_200_000  # aproksimasi; dipertajam di bawah
    try:
        cur_block = int(conn.execute(
            "select max(block_num) from price_points").fetchone()[0])
    except Exception:
        pass
    cutoff = cur_block - IDLE_DAYS * BLOCKS_PER_DAY

    dormant = [r[0] for r in conn.execute("""
        select a from (
          select lower(se.wallet_address) a, count(*) n, max(se.block_num) mx
          from swap_events se
          group by lower(se.wallet_address)
          having count(*) between 1 and 2
        ) s
        join wallet_labels wl on lower(wl.wallet_address) = s.a
        where wl.label = 'GENERALIST'
          and lower(s.a) not in (select lower(wallet_address) from wallet_labels
                                  where label != 'GENERALIST')
          and s.mx < ?
        group by a
    """, (cutoff,))]
    for a in dormant:
        conn.execute(
            """insert into wallet_labels (wallet_address, label, confidence,
                 evidence, assigned_at)
               values (?, 'DORMANT', 0.9, ?, ?)
               on conflict(wallet_address, label) do nothing""",
            (a, json.dumps({"rule": "1-2 swap, max block < cutoff 30d",
                            "cutoff_block": cutoff}), now))
    print(f"DORMANT dicatat: {len(dormant)} wallet")

    active = [r[0] for r in conn.execute("""
        select a from (
          select lower(se.wallet_address) a, count(*) n, max(se.block_num) mx
          from swap_events se
          group by lower(se.wallet_address)
          having count(*) >= 3
        ) s
        join wallet_labels wl on lower(wl.wallet_address) = s.a
        where wl.label = 'GENERALIST'
          and lower(s.a) not in (select lower(wallet_address) from wallet_labels
                                  where label != 'GENERALIST')
          and s.mx >= ?
        group by a
    """, (cutoff,))]
    for a in active:
        conn.execute(
            """insert into wallet_labels (wallet_address, label, confidence,
                 evidence, assigned_at)
               values (?, 'ACTIVE_MIN', 0.9, ?, ?)
               on conflict(wallet_address, label) do nothing""",
            (a, json.dumps({"rule": ">=3 swap & aktif <=30 hari; belum lolos klasifikasi lain"}),
             now))
    print(f"ACTIVE_MIN dicatat: {len(active)} wallet")
    conn.commit()
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
