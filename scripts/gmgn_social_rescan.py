"""Rescan X-handle & profil sosial wallet DB via GMGN OpenAPI wallet_stats.

PENEMUAN KUNCI (2026-10-04): wallet_stats menyertakan objek `common` berisi
twitter_username, twitter_name, twitter_fans_num, tags, tag_rank,
created_token_count, fund_from_address, fund_amount — data yang selama ini
dianggap hanya ada di web GMGN ternyata ADA di API resmi.

Target prioritas (default): wallet dgn swap terbanyak + label menarik.
Skala penuh: --all-swaps N (semua wallet swaps>=N) — cocok [VPS] malam hari.

Output: tabel wallet_social (PK address+source) — resumable, idempoten.
  address, source='gmgn_openapi', twitter_username, twitter_name, twitter_fans,
  name, tags(json), extra(json: realized_profit_7d, winrate, fund_from_address,
  created_token_count, ...), updated_at.

Pemakaian:
  python scripts/gmgn_social_rescan.py --limit 50          # prioritas
  python scripts/gmgn_social_rescan.py --all-swaps 20      # skala [VPS]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

DB = REPO / "data" / "topwallet.db"
CHECKPOINT = REPO / "results" / "gmgn_social_rescan_state.json"
BATCH_SAVE = 25

SCHEMA = """
CREATE TABLE IF NOT EXISTS wallet_social (
  address TEXT NOT NULL,
  source TEXT NOT NULL,
  twitter_username TEXT,
  twitter_name TEXT,
  twitter_fans INTEGER,
  name TEXT,
  tags TEXT,
  extra TEXT,
  updated_at TEXT,
  PRIMARY KEY (address, source)
)
"""

PRIORITY_LABELS = ("INSIDER", "CT_ATTRIBUTED", "WHALE", "WHALE_SUS",
                   "DEV", "DEV_SERIAL_RUGGER", "SNIPER", "MEV_BOT")


def load_state() -> dict:
    if CHECKPOINT.exists():
        return json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    return {"done": 0, "with_twitter": 0, "scanned": [], "started_at":
            datetime.now(timezone.utc).isoformat()}


def save_state(st: dict) -> None:
    CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    tmp = CHECKPOINT.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(CHECKPOINT)


def pick_targets(conn: sqlite3.Connection, limit: int, all_swaps: int | None) -> list[str]:
    done = {r[0] for r in conn.execute(
        "select address from wallet_social where source='gmgn_openapi'")}
    # S-50: precompute lowercase aggregates SEKALI (subquery per-wallet di
    # 157K wallets = O(N*M), pernah stuck >10 menit tanpa output).
    conn.executescript("""
        create temp table if not exists _swapcnt as
          select lower(wallet_address) a, count(*) n
          from swap_events group by 1;
        create index if not exists temp._swapcnt_a on _swapcnt(a);
        create temp table if not exists _labprio as
          select distinct lower(wallet_address) a
          from wallet_labels
          where label in ('INSIDER','CT_ATTRIBUTED','WHALE','WHALE_SUS',
                          'DEV','DEV_SERIAL_RUGGER','SNIPER','MEV_BOT');
        create index if not exists temp._labprio_a on _labprio(a);
    """)
    if all_swaps is not None:
        rows = conn.execute(
            """select lower(w.address) from wallets w
               join _swapcnt sc on sc.a = lower(w.address)
               where sc.n >= ? and lower(w.address) not in (
                   select address from wallet_social where source='gmgn_openapi')
               order by sc.n desc""", (all_swaps,)).fetchall()
    else:
        rows = conn.execute(
            """select wa
               from (select lower(w.address) wa,
                            (lp.a is not null) prio,
                            coalesce(max(sc.n), 0) n
                     from wallets w
                     left join _swapcnt sc on sc.a = lower(w.address)
                     left join _labprio lp on lp.a = lower(w.address)
                     where lower(w.address) not in (
                       select address from wallet_social
                       where source='gmgn_openapi')
                     group by wa)
               order by prio desc, n desc
               limit ?""",
            (limit,)).fetchall()
    return [r[0] for r in rows if r[0] and r[0] not in done]
    return [r[0] for r in rows if r[0] and r[0] not in done]


def upsert(conn: sqlite3.Connection, rows: list[dict]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.executemany(
        """insert into wallet_social (address, source, twitter_username,
             twitter_name, twitter_fans, name, tags, extra, updated_at)
           values (:address, 'gmgn_openapi', :twitter_username, :twitter_name,
             :twitter_fans, :name, :tags, :extra, :updated_at)
           on conflict(address, source) do update set
             twitter_username=excluded.twitter_username,
             twitter_name=excluded.twitter_name,
             twitter_fans=excluded.twitter_fans,
             name=excluded.name, tags=excluded.tags, extra=excluded.extra,
             updated_at=excluded.updated_at
           where excluded.updated_at > wallet_social.updated_at""",
        [{**r, "updated_at": now} for r in rows])


async def main_async(args) -> int:
    from src.discover.gmgn_client import GmgnClient

    conn = sqlite3.connect(DB, timeout=60)
    conn.execute("pragma busy_timeout=60000")
    conn.execute(SCHEMA)
    targets = pick_targets(conn, args.limit, args.all_swaps)
    print(f"target rescan: {len(targets)} wallet "
          f"(limit={args.limit} all_swaps={args.all_swaps})", flush=True)
    if not targets:
        print("tidak ada target — selesai")
        return 0

    st = load_state()
    cli = GmgnClient(rps=args.rps)
    buf: list[dict] = []
    n_tw = 0
    try:
        for i, addr in enumerate(targets, 1):
            try:
                s = await asyncio.to_thread(
                    cli.wallet_stats, "robinhood", addr, "7d")
            except Exception as e:
                s = None
                print(f"[{i}/{len(targets)}] {addr[:12]} ERR {str(e)[:60]}", flush=True)
            common = (s or {}).get("common") or {}
            tw = common.get("twitter_username") or ""
            row = {
                "address": addr,
                "twitter_username": tw,
                "twitter_name": common.get("twitter_name") or "",
                "twitter_fans": common.get("twitter_fans_num") or
                                common.get("followers_count"),
                "name": common.get("name") or common.get("nick_name") or "",
                "tags": json.dumps(common.get("tags") or []),
                "extra": json.dumps({
                    "realized_profit_7d": (s or {}).get("realized_profit"),
                    "pnl_7d": (s or {}).get("realized_profit_pnl"),
                    "winrate_7d": ((s or {}).get("pnl_stat") or {}).get("winrate"),
                    "token_num_7d": ((s or {}).get("pnl_stat") or {}).get("token_num"),
                    "created_token_count": common.get("created_token_count"),
                    "fund_from_address": common.get("fund_from_address"),
                    "fund_amount": common.get("fund_amount"),
                    "is_blue_verified": common.get("is_blue_verified"),
                }),
            }
            buf.append(row)
            if tw:
                n_tw += 1
            if len(buf) >= BATCH_SAVE or i == len(targets):
                conn.executemany  # noqa
                upsert(conn, buf)
                conn.commit()
                buf = []
            st["done"] += 1
            if tw:
                st["with_twitter"] = (st.get("with_twitter") or 0) + 1
            if i % 50 == 0:
                save_state(st)
                print(f"[{i}/{len(targets)}] twitter={n_tw} ({n_tw/i:.0%})", flush=True)
            time.sleep(0)
    finally:
        cli.close()
        if buf:
            upsert(conn, buf)
            conn.commit()
        save_state(st)
        conn.close()
    print(f"SELESAI: {len(targets)} discan, {n_tw} dapat X handle "
          f"({n_tw/max(len(targets),1):.0%})")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--all-swaps", type=int, default=None,
                    help="scan semua wallet dengan swaps >= N (skala penuh)")
    ap.add_argument("--rps", type=float, default=1.5)
    args = ap.parse_args()
    sys.exit(asyncio.run(main_async(args)))
