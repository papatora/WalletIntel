"""Label POOL_CONTRACT & NOISE — bersihkan leaderboard dari non-trader (S-50c).

POOL_CONTRACT: eth_getCode != 0x → kontrak (pool/arb/router) yang ikut
  tertelan enrichment. Target: top-N |net| + semua labeled non-GENERALIST.
  conf 0.98, evidence {code_len}.
NOISE: total swap == 1 DAN on-chain tidak ada transaksi terbaru (Etherscan V2,
  max_pages=1: blok tx terakhir < cutoff → NOISE). conf 0.90.

Idempoten; hasil → wallet_labels (label POOL_CONTRACT / NOISE).
Setelah jalan: refresh_results_local + POST /api/rebuild.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

DB = REPO / "data" / "topwallet.db"
PRIORITY = ("INSIDER", "CT_ATTRIBUTED", "WHALE", "WHALE_SUS", "DEV",
            "DEV_SERIAL_RUGGER", "SNIPER", "MEV_BOT", "BOT", "SNIPER_BOT")


def upsert_label(conn, addr, label, conf, ev, now):
    conn.execute(
        """insert into wallet_labels (wallet_address, label, confidence,
             evidence, assigned_at)
           values (?, ?, ?, ?, ?)
           on conflict(wallet_address, label) do update set
             confidence=excluded.confidence,
             evidence=excluded.evidence,
             assigned_at=excluded.assigned_at""",
        (addr, label, conf, json.dumps(ev), now))


async def pool_contracts(conn, top_n: int) -> int:
    from src.utils.rpc_client import EvmRpcClient
    now = datetime.now(timezone.utc).isoformat()
    # kandidat: top |net| + labeled non-generalist
    nets = {}
    for wa, usd, side in conn.execute(
            "select lower(wallet_address), usd_value, side from swap_events"):
        if usd is None:
            continue
        nets[wa] = nets.get(wa, 0) + (usd if side == "SELL" else -usd)
    top = [a for a, _ in sorted(nets.items(), key=lambda kv: -abs(kv[1]))[:top_n]]
    labeled = [r[0].lower() for r in conn.execute(
        "select distinct lower(wallet_address) from wallet_labels "
        "where label in (" + ",".join("?" * len(PRIORITY)) + ")", PRIORITY)]
    candidates = list(dict.fromkeys(top + labeled))
    # buang yang sudah POOL_CONTRACT
    have = {r[0].lower() for r in conn.execute(
        "select wallet_address from wallet_labels where label='POOL_CONTRACT'")}
    candidates = [a for a in candidates if a not in have]
    print(f"pool-contract check: {len(candidates)} wallet", flush=True)

    cli = EvmRpcClient()
    n_contract = 0
    try:
        CH = 100
        for i in range(0, len(candidates), CH):
            chunk = candidates[i:i + CH]
            try:
                res = await cli.batch_call(
                    [("eth_getCode", [a, "latest"]) for a in chunk])
            except Exception as e:
                print(f"  batch {i} err {str(e)[:80]}", flush=True)
                continue
            for a, code in zip(chunk, res):
                code = code if isinstance(code, str) else None
                if code and code != "0x":
                    upsert_label(conn, a, "POOL_CONTRACT", 0.98,
                                 {"code_len": len(code) - 2}, now)
                    n_contract += 1
            conn.commit()
            print(f"  [{i + len(chunk)}/{len(candidates)}] contracts so far: {n_contract}",
                  flush=True)
    finally:
        pass
    return n_contract


async def noise(conn, limit: int, idle_days: int) -> int:
    from src.utils.etherscan_client import make_explorer_client
    now = datetime.now(timezone.utc).isoformat()
    cutoff_block = None
    rows = conn.execute("""
        select lower(se.wallet_address), max(se.block_num), count(*)
        from swap_events se
        group by lower(se.wallet_address)
        having count(*) = 1
        order by max(se.block_num) asc
        limit ?
    """, (limit,)).fetchall()
    cand = [r for r in rows if r[0]]
    print(f"noise check: {len(cand)} wallet 1-swap (oldest first)", flush=True)
    cli = make_explorer_client()
    from src.utils.rpc_client import EvmRpcClient
    bn_cli = EvmRpcClient()
    current_block = await bn_cli.block_number()
    cutoff_block = current_block - idle_days * 864_000
    print(f"current_block={current_block:,} cutoff(idle {idle_days}d)={cutoff_block:,}",
          flush=True)
    n_noise = 0
    try:
        for i, (addr, blk, _n) in enumerate(cand, 1):
            try:
                txs = await cli.address_transactions(addr, max_pages=1)
                last_blk = max((int(t.get("block_number") or 0) for t in txs or []),
                               default=0)
                if last_blk and last_blk < cutoff_block:
                    upsert_label(conn, addr, "NOISE", 0.90,
                                 {"last_onchain_block": last_blk,
                                  "cutoff_block": cutoff_block,
                                  "reason": "1 swap di DB, tidak ada tx on-chain terbaru"},
                                 now)
                    n_noise += 1
            except Exception as e:
                print(f"  [{i}] {addr[:12]} ERR {str(e)[:60]}", flush=True)
            if i % 25 == 0:
                conn.commit()
                print(f"  [{i}/{len(cand)}] noise so far: {n_noise}", flush=True)
            await asyncio.sleep(0.12)
    finally:
        conn.commit()
    return n_noise


async def _noop():
    return None


async def main_async(args):
    conn = sqlite3.connect(DB, timeout=60)
    conn.execute("pragma busy_timeout=60000")
    if args.mode in ("contracts", "all"):
        n = await pool_contracts(conn, args.top_n)
        print(f"POOL_CONTRACT baru: {n}")
    if args.mode in ("noise", "all"):
        n = await noise(conn, args.noise_limit, args.idle_days)
        print(f"NOISE baru: {n}")
    conn.close()
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["contracts", "noise", "all"], default="all")
    ap.add_argument("--top-n", type=int, default=2000)
    ap.add_argument("--noise-limit", type=int, default=400)
    ap.add_argument("--idle-days", type=int, default=30)
    args = ap.parse_args()
    sys.exit(asyncio.run(main_async(args)))
