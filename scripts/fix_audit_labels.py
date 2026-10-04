"""Perbaikan label pasca-audit A-J (temuan G-F-P1/H-P1 terverifikasi).

1. UN-NOISE: hapus label NOISE untuk wallet yang real-latest tx (Etherscan
   sort=desc) >= cutoff — audit G: 52 FP karena asc+max_pages=1.
2. POOL_CONTRACT re-classify: code 23 byte prefix 0xef0100 = EIP-7702
   delegated EOA (BUKAN kontrak) → hapus label POOL_CONTRACT (label asli
   INSIDER/dkk otomatis kembali jadi primary). Kontrak asli (code besar /
   bukan 0xef designator) dipertahankan.
3. Prune CT_ATTRIBUTED legacy: conf 0.6 dgn addr tanpa x_primary (15 stale).
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

DB = REPO / "data" / "topwallet.db"
IDLE_DAYS = 30
BLOCKS_PER_DAY = 864_000


async def main_async() -> int:
    from src.utils.etherscan_client import make_explorer_client
    from src.utils.rpc_client import EvmRpcClient

    conn = sqlite3.connect(DB, timeout=60)
    conn.execute("pragma busy_timeout=60000")
    now = datetime.now(timezone.utc).isoformat()
    cli = make_explorer_client()
    rpc = EvmRpcClient()

    # ---- 1. NOISE re-check (desc) --------------------------------------
    noise = [r[0].lower() for r in conn.execute(
        "select wallet_address from wallet_labels where label='NOISE'")]
    print(f"NOISE terpasang: {len(noise)} — re-check desc", flush=True)
    removed_noise = 0
    codes = {}
    CH = 50
    try:
        for i in range(0, len(noise), CH):
            chunk = noise[i:i + CH]
            try:
                codes_batch = await rpc.batch_call(
                    [("eth_getCode", [a, "latest"]) for a in chunk])
            except Exception as e:
                print(f"  batch code err {str(e)[:60]}", flush=True)
                continue
            for a, code in zip(chunk, codes_batch):
                code = code if isinstance(code, str) else "0x"
                is_eoa = code == "0x"
                is_7702 = code.startswith("0xef0100")
                codes[a] = (is_eoa, is_7702, len(code) - 2 if code else 0)
        for a in noise:
            is_eoa, is_7702, clen = codes.get(a, (False, False, -1))
            if not is_eoa:
                continue  # kontrak/7702 — tangani di POOL_CONTRACT pass
            try:
                txs = await cli.address_transactions(a, max_pages=1, sort="desc")
                last_blk = max((int(t.get("block_number") or 0) for t in txs or []),
                               default=0)
                cur = await rpc.block_number()
                cutoff = cur - IDLE_DAYS * BLOCKS_PER_DAY
                if last_blk >= cutoff:
                    conn.execute(
                        "delete from wallet_labels where wallet_address=? and label='NOISE'",
                        (a,))
                    removed_noise += 1
            except Exception as e:
                print(f"  {a[:12]} ERR {str(e)[:60]}", flush=True)
            if removed_noise and removed_noise % 10 == 0:
                conn.commit()
        conn.commit()
        print(f"NOISE FP dihapus: {removed_noise}", flush=True)

        # ---- 2. POOL_CONTRACT re-classify (7702 vs kontrak asli) --------
        pool = [r[0].lower() for r in conn.execute(
            "select wallet_address from wallet_labels where label='POOL_CONTRACT'")]
        print(f"POOL_CONTRACT terpasang: {len(pool)} — re-check code", flush=True)
        removed_pool = kept_pool = 0
        for i in range(0, len(pool), CH):
            chunk = pool[i:i + CH]
            try:
                codes_batch = await rpc.batch_call(
                    [("eth_getCode", [a, "latest"]) for a in chunk])
            except Exception as e:
                print(f"  batch err {str(e)[:60]}", flush=True)
                continue
            for a, code in zip(chunk, codes_batch):
                code = code if isinstance(code, str) else "0x"
                byte_len = (len(code) - 2) // 2 if code.startswith("0x") else 0
                if code.startswith("0xef0100") and byte_len == 23:
                    # EIP-7702 delegated EOA = smart account trader, bukan pool
                    conn.execute(
                        "delete from wallet_labels where wallet_address=? and label='POOL_CONTRACT'",
                        (a,))
                    removed_pool += 1
                elif code and code != "0x":
                    up = json.dumps({"code_len_bytes": byte_len,
                                     "recheck": now})
                    conn.execute(
                        "update wallet_labels set evidence=? where wallet_address=? and label='POOL_CONTRACT'",
                        (up, a))
                    kept_pool += 1
            conn.commit()
            print(f"  [{min(i+CH, len(pool))}/{len(pool)}] removed={removed_pool} kept={kept_pool}",
                  flush=True)
    finally:
        pass

    # ---- 3. Prune CT legacy (conf 0.6, tanpa x_primary) -----------------
    stale = [r[0].lower() for r in conn.execute("""
        select wl.wallet_address from wallet_labels wl
        where wl.label='CT_ATTRIBUTED' and wl.confidence=0.6
          and lower(wl.wallet_address) not in (
            select address from wallet_social where coalesce(x_primary,'') != '')
    """)]
    for a in stale:
        conn.execute(
            "delete from wallet_labels where wallet_address=? and label='CT_ATTRIBUTED'",
            (a,))
    conn.commit()
    print(f"CT_ATTRIBUTED legacy stale dihapus: {len(stale)}")

    n_noise = conn.execute("select count(*) from wallet_labels where label='NOISE'").fetchone()[0]
    n_pool = conn.execute("select count(*) from wallet_labels where label='POOL_CONTRACT'").fetchone()[0]
    n_ct = conn.execute("select count(*) from wallet_labels where label='CT_ATTRIBUTED'").fetchone()[0]
    conn.close()
    print(f"FINAL: NOISE={n_noise} POOL_CONTRACT={n_pool} CT_ATTRIBUTED={n_ct}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
