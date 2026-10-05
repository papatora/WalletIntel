"""Auto-label CT_ATTRIBUTED untuk semua wallet ber-X-identity (mandat user 2026-10-05).

Sumber: wallet_social (dual-source gmgn+arkham, x_primary).
Rule:
  - x_primary != '' → label CT_ATTRIBUTED
  - confidence: 0.90 dual-verified (gmgn+arkham cocok)
              | 0.75 gmgn saja
              | 0.65 arkham saja
  - evidence json: {x_gmgn, x_arkham, x_conflict, fans}
  - x_conflict → tetap dilabel (identitas sosial ada) + evidence menunjukkan
    kedua handle — analyst harus cek manual (jangan dipilih diam-diam).

Idempoten: on conflict update. Setelah apply → refresh_results_local +
rebuild explorer dataset (POST /api/rebuild).
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DB = REPO / "data" / "topwallet.db"


def main() -> int:
    conn = sqlite3.connect(DB, timeout=60)
    conn.execute("pragma busy_timeout=60000")
    rows = conn.execute("""
        select address, coalesce(x_gmgn,''), coalesce(x_arkham,''),
               coalesce(x_primary,''),
               case when coalesce(x_conflict,'0') in ('1','true','True') then 1 else 0 end
        from wallet_social
        where coalesce(x_primary,'') != ''
        group by address
    """).fetchall()
    now = datetime.now(timezone.utc).isoformat()
    applied = 0
    conflicts = 0
    for addr, g, a, p, conf in rows:
        conf_val = 0.90 if (g and a and not conf) else (0.75 if g else 0.65)
        ev = json.dumps({"x_gmgn": g, "x_arkham": a, "x": p,
                         "x_conflict": bool(conf)})
        conn.execute(
            """insert into wallet_labels (wallet_address, label, confidence,
                 evidence, assigned_at)
               values (?, 'CT_ATTRIBUTED', ?, ?, ?)
               on conflict(wallet_address, label) do update set
                 confidence=excluded.confidence,
                 evidence=excluded.evidence,
                 assigned_at=excluded.assigned_at""",
            (addr, conf_val, ev, now))
        applied += 1
        if conf:
            conflicts += 1
    conn.commit()

    # ringkasan
    n = conn.execute(
        "select count(*) from wallet_labels where label='CT_ATTRIBUTED'").fetchone()[0]
    conn.close()
    print(f"CT_ATTRIBUTED di-apply utk {applied} wallet ber-X "
          f"(total label CT_ATTRIBUTED sekarang: {n}; konflik: {conflicts})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
