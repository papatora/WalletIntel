"""Merge X-handle multi-sumber dengan DUAL-SCAN policy (user mandate 2026-10-05):

ATURAN:
1. Kedua sumber (gmgn + arkham) WAJIB discan untuk wallet yang sama —
   menemukan X di satu sumber BUKAN alasan skip sumber lain (verifikasi).
2. Simpan KEDUA handle bila keduanya ada: x_gmgn + x_arkham.
3. Handle beda antar sumber → x_conflict=true (ditampilkan apa adanya,
   TIDAK dipilih salah satu secara diam-diam).
4. Handle final utk tampilan (x_primary): gmgn jika ada, else arkham —
   tapi conflict tetap tercatat.

Input:
  wallet_social (source='gmgn_openapi' | 'gmgn_rank' | 'arkham')
  results/arkham_entities.json (@entity / x_handle)
Output:
  tabel wallet_social diperkaya kolom x_gmgn/x_arkham/x_conflict/x_primary
  + known_entities.json update (name + x utk yang belum ada)
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DB = REPO / "data" / "topwallet.db"

ALTERS = [
    "alter table wallet_social add column x_gmgn text",
    "alter table wallet_social add column x_arkham text",
    "alter table wallet_social add column x_conflict integer default 0",
    "alter table wallet_social add column x_primary text",
]


def norm(h: str | None) -> str:
    return (h or "").strip().lstrip("@")


def main() -> int:
    conn = sqlite3.connect(DB)
    for a in ALTERS:
        try:
            conn.execute(a)
        except sqlite3.OperationalError:
            pass  # sudah ada

    # ---- sumber arkham → rows source='arkham' ----
    ark_path = REPO / "results" / "arkham_entities.json"
    n_ark = 0
    if ark_path.exists():
        ark = json.loads(ark_path.read_text(encoding="utf-8"))
        now = datetime.now(timezone.utc).isoformat()
        rows = []
        for addr, v in ark.items():
            if not isinstance(v, dict):
                continue
            h = norm(v.get("x_handle") or "")
            ent = (v.get("entity") or "").strip()
            if not h and not ent.startswith("@"):
                # tetap simpan entity non-X (CEX dll) utk kepentuian lain?
                continue
            if not h and ent.startswith("@"):
                h = norm(ent)
            if not h:
                continue
            rows.append((addr.lower(), "arkham", h))
        for a, src, h in rows:
            conn.execute(
                """insert into wallet_social (address, source, twitter_username,
                     twitter_name, updated_at)
                   values (?, 'arkham', ?, '', ?)
                   on conflict(address, source) do update set
                     twitter_username=excluded.twitter_username,
                     updated_at=excluded.updated_at""",
                (a, h, now))
        n_ark = len(rows)
    conn.commit()
    print(f"arkham X handles masuk: {n_ark}")

    # ---- gmgn rank → rows source='gmgn_rank' ----
    rank_path = REPO / "results" / "gmgn_web" / "gmgn_rank_social.json"
    n_rank = 0
    if rank_path.exists():
        doc = json.loads(rank_path.read_text(encoding="utf-8"))
        now = datetime.now(timezone.utc).isoformat()
        for addr, v in (doc.get("profiles") or {}).items():
            h = norm(v.get("twitter_username"))
            conn.execute(
                """insert into wallet_social (address, source, twitter_username,
                     twitter_name, tags, extra, updated_at)
                   values (?, 'gmgn_rank', ?, ?, ?, ?, ?)
                   on conflict(address, source) do update set
                     twitter_username=excluded.twitter_username,
                     twitter_name=excluded.twitter_name,
                     tags=excluded.tags, extra=excluded.extra,
                     updated_at=excluded.updated_at""",
                (addr, h, v.get("twitter_name") or "",
                 json.dumps(v.get("tags") or []),
                 json.dumps({k: v.get(k) for k in
                             ("pnl_30d", "winrate_30d", "realized_profit_30d",
                              "sources", "caller_avg_multiplier")}), now))
            n_rank += 1
        conn.commit()
    print(f"gmgn rank profiles masuk: {n_rank}")

    # ---- kolom dual-X ----
    conn.execute("""
        update wallet_social set
          x_gmgn = coalesce(
            (select twitter_username from wallet_social g
              where g.address=wallet_social.address
                and g.source in ('gmgn_openapi','gmgn_rank')
                and coalesce(twitter_username,'') != ''
              limit 1), ''),
          x_arkham = coalesce(
            (select twitter_username from wallet_social a
              where a.address=wallet_social.address
                and a.source='arkham'
                and coalesce(twitter_username,'') != ''
              limit 1), '')
        where source='gmgn_openapi'
           or source in ('gmgn_rank','arkham')
    """)
    conn.execute("""
        update wallet_social set
          x_conflict = case when x_gmgn != '' and x_arkham != ''
                             and lower(x_gmgn) != lower(x_arkham)
                            then 1 else 0 end,
          x_primary = case when x_gmgn != '' then x_gmgn else x_arkham end
    """)
    conn.commit()

    n_both = conn.execute(
        "select count(*) from (select distinct address from wallet_social "
        "where x_gmgn != '' and x_arkham != '')").fetchone()[0]
    n_conf = conn.execute(
        "select count(*) from (select distinct address from wallet_social "
        "where x_conflict = 1)").fetchone()[0]
    n_prim = conn.execute(
        "select count(*) from (select distinct address from wallet_social "
        "where coalesce(x_primary,'') != '')").fetchone()[0]
    print(f"dual-source X: {n_both} wallet | CONFLICT: {n_conf} | punya X: {n_prim}")

    # ---- known_entities: tambahkan X utk alamat yg belum berlabel ----
    ke_path = REPO / "Database Local only" / "html" / "data" / "known_entities.json"
    ke = json.loads(ke_path.read_text(encoding="utf-8"))
    ents = ke["entities"]
    added = 0
    for addr, x, conf in conn.execute(
            "select distinct address, x_primary, x_conflict from wallet_social "
            "where coalesce(x_primary,'') != ''"):
        a = addr.lower()
        if a not in ents:
            ents[a] = {"name": f"@{x}", "type": "OTHER",
                       "source": "x:gmgn+arkham" if conf else "x:multi",
                       "x": x}
            added += 1
        else:
            ents[a]["x"] = x
            if conf:
                ents[a]["x_conflict"] = True
    ke["entities"] = ents
    tmp = ke_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(ke, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(ke_path)
    print(f"known_entities: +{added} entitas X baru (total {len(ents)})")

    # laporan konflik utk review
    confl = conn.execute(
        "select distinct address, x_gmgn, x_arkham from wallet_social "
        "where x_conflict = 1 limit 30").fetchall()
    if confl:
        print("contoh konflik (gmgn vs arkham):")
        for a, g, k in confl[:10]:
            print(f"  {a[:14]}… gmgn=@{g} arkham=@{k}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
