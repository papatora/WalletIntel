"""KERUCUTKAN DB LOKAL — S-53 (mandat user 2026-10-12): DB makan GB terlalu
besar; buang yang benar-benar noise / tidak worth simpan di PC.

BUKTI AUDIT (DB 9 Okt, file 2,84 GB, freelist ~0 = padat, bukan bloat):
  - price_points 7,6 jt rows = 0,88 GB data + index terbesar
      * 2 pool MATI (token tanpa SATU swap pun) hisap 1,28 jt poin (16,9%)
        = bangkai murni utk derived pricing lokal (tak ada swap utk dihargai)
      * pool dgn 11-100 swap: 831 rb poin — cukup ~400/pool utk nearest-block
  - index swap_events (ts/wallet/token) di PC tak terpakai pola baca kita
    (dataset/playbook full-scan; VPS tetap punya index-nya)  ~= ratusan MB
  - wallet "noise" (<=2 swap, idle >60 hari, tanpa label khusus): 80.915
    wallet TAPI cuma 227 baris swap (~15-20 MB) -> dibuang utk KEBERSIHAN
    dataset, bukan utk hemat GB (jujur: ini bukan penghemat disk)
  - yang TIDAK disentuh: swap_events data, wallet berlabel khusus apapun,
    wallet_scores, pool >100 swap (series penuh utk playbook/pump)

Idempoten + dry-run default. Laporan: results/kerucutkan_report.json.
Pemakaian:
  python scripts/kerucutkan.py            # audit + rencana (tanpa tulis)
  python scripts/kerucutkan.py --apply    # eksekusi + VACUUM + export kanonik
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DB = REPO / "data" / "topwallet.db"
OUT = REPO / "results" / "kerucutkan_report.json"

IDLE_DAYS = 60          # wallet tanpa aktivitas > ini = dormant
MAX_SWAPS_KEEP = 2      # <= ini + dormant + tanpa label khusus = noise
KEEP_POINTS_SMALL = 400   # pool 11-100 swap: cap poin
KEEP_POINTS_TINY = 200    # pool 1-10 swap: cap poin
PROTECT_SWAPS = 100     # pool >100 swap: series PENUH
MAX_WALLET_PRUNE_PCT = 60  # sanity: Tolak bila prune >60% wallet

# label yang menyelamatkan wallet dari prune (selain bucket generik)
KEEP_LABEL_PREFIXES_OK = {"GENERALIST", "ACTIVE_MIN", "DORMANT", "DUST"}
DROP_INDEXES = [
    "ix_swap_events_ts",
    "ix_swap_events_wallet_address",
    "ix_swap_events_token_address",
]


def mb(n: int) -> str:
    return f"{n / 1e6:.1f} MB"


def audit(conn: sqlite3.Connection) -> dict:
    """Hitung rencana tanpa menulis."""
    max_ts = conn.execute("select max(ts) from swap_events").fetchone()[0]
    cutoff = (datetime.strptime(max_ts[:19], "%Y-%m-%d %H:%M:%S")
              - timedelta(days=IDLE_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
    plan: dict = {"db_max_ts": max_ts, "idle_cutoff": cutoff}

    # ---- wallet noise ----
    protected = set()
    generic = set()
    noise_lab = set()
    for w, l in conn.execute("select wallet_address, label from wallet_labels"):
        base = l.split(":")[0]
        if base == "NOISE":
            noise_lab.add(w)
        elif base in KEEP_LABEL_PREFIXES_OK:
            generic.add(w)
        else:
            protected.add(w)
    n_wallets = conn.execute("select count(*) from wallets").fetchone()[0]
    cand, cand_swaps = [], 0
    for addr, nsw, last in conn.execute(
            "select w.address, count(s.id), max(s.ts) from wallets w "
            "left join swap_events s on s.wallet_address=w.address "
            "group by w.address"):
        if addr in protected:
            continue
        if addr in noise_lab:
            cand.append(addr)
            cand_swaps += nsw or 0
        elif (nsw or 0) <= MAX_SWAPS_KEEP and (last or "") < cutoff:
            cand.append(addr)
            cand_swaps += nsw or 0
    plan["wallets_total"] = n_wallets
    plan["wallet_prune"] = {"count": len(cand),
                            "pct": round(100 * len(cand) / max(n_wallets, 1), 1),
                            "swap_rows": cand_swaps}
    plan["_prune_list"] = cand

    # ---- price_points ----
    pts_total = conn.execute("select count(*) from price_points").fetchone()[0]
    dead = conn.execute(
        "select count(*) from price_points where pool_address in ("
        " select p.address from pools p where not exists ("
        "  select 1 from swap_events s where s.token_address=p.token_address))"
    ).fetchone()[0]
    small = conn.execute(
        f"""select p.address, count(*) n, (
              select count(*) from swap_events s where s.token_address=p.token_address) nsw
            from price_points pp join pools p on p.address=pp.pool_address
            group by p.address
            having nsw > 0 and nsw <= {PROTECT_SWAPS} and n > min(
              case when nsw <= 10 then {KEEP_POINTS_TINY} else {KEEP_POINTS_SMALL} end, n)"""
    ).fetchall()
    small_cut = sum(max(0, n - (KEEP_POINTS_TINY if nsw <= 10 else KEEP_POINTS_SMALL))
                    for _, n, nsw in small)
    plan["price_points"] = {
        "total": pts_total,
        "dead_pool_rows": dead,
        "downsample_pools": len(small),
        "downsample_rows": small_cut,
    }
    plan["_small_pools"] = [(p, KEEP_POINTS_TINY if nsw <= 10 else KEEP_POINTS_SMALL)
                            for p, n, nsw in small]
    idx = {n: conn.execute(
        "select count(*) from sqlite_master where type='index' and name=?",
        (n,)).fetchone()[0] for n in DROP_INDEXES}
    plan["indexes_present"] = {k: bool(v) for k, v in idx.items()}
    return plan


def apply(conn: sqlite3.Connection, plan: dict) -> dict:
    t0 = time.time()
    done = {}
    lst = plan["_prune_list"]

    # sanity: jangan pernah prune >MAX_WALLET_PRUNE_PCT wallet
    if plan["wallet_prune"]["pct"] > MAX_WALLET_PRUNE_PCT:
        sys.exit(f"ABORT: rencana prune {plan['wallet_prune']['pct']}% wallet "
                 f"> batas {MAX_WALLET_PRUNE_PCT}% — cek datanya dulu")

    conn.execute("begin")
    # 1. wallet noise + jejaknya
    step = 5000
    n_sw = n_lab = n_soc = n_wal = 0
    for i in range(0, len(lst), step):
        chunk = lst[i:i + step]
        ph = ",".join("?" * len(chunk))
        n_sw += conn.execute(
            f"delete from swap_events where wallet_address in ({ph})", chunk).rowcount
        n_lab += conn.execute(
            f"delete from wallet_labels where wallet_address in ({ph})", chunk).rowcount
        n_soc += conn.execute(
            f"delete from wallet_social where address in ({ph})", chunk).rowcount
        n_wal += conn.execute(
            f"delete from wallets where address in ({ph})", chunk).rowcount
    done["wallet_prune"] = {"wallets": n_wal, "swap_events": n_sw,
                            "wallet_labels": n_lab, "wallet_social": n_soc}

    # 2. price_points pool mati
    dead = conn.execute(
        "delete from price_points where pool_address in ("
        " select p.address from pools p where not exists ("
        "  select 1 from swap_events s where s.token_address=p.token_address))"
    ).rowcount
    done["price_points_dead_pool"] = dead

    # 3. downsample pool kecil (pertahankan titik pertama+terakhir, sisanya merata)
    ds = 0
    for pool, keep in plan["_small_pools"]:
        rows = [r[0] for r in conn.execute(
            "select id from price_points where pool_address=? order by block_num",
            (pool,))]
        if len(rows) <= keep:
            continue
        stride = max(1, (len(rows) - 1) // (keep - 1))
        keep_ids = set(rows[::stride])
        keep_ids.add(rows[-1])
        drop = [i for i in rows if i not in keep_ids]
        for j in range(0, len(drop), 5000):
            ph = ",".join("?" * len(drop[j:j + 5000]))
            ds += conn.execute(
                f"delete from price_points where id in ({ph})",
                drop[j:j + 5000]).rowcount
    done["price_points_downsample"] = ds
    conn.execute("commit")

    # 4. index lokal tak terpakai (rebuild berikutnya bikin lagi; kerucutkan
    #    jalan lagi tiap delta via hook night_delta)
    dropped = []
    for n in DROP_INDEXES:
        if plan["indexes_present"].get(n):
            conn.execute(f"drop index if exists {n}")
            dropped.append(n)
    done["indexes_dropped"] = dropped

    done["vacuum_s"] = 0
    return done


def main() -> int:
    do_apply = "--apply" in sys.argv
    if not DB.exists():
        sys.exit("DB tidak ada")
    size_before = DB.stat().st_size
    conn = sqlite3.connect(DB)
    conn.execute("pragma busy_timeout=60000")

    plan = audit(conn)
    prune_pct = plan["wallet_prune"]["pct"]
    print(f"[kerucutkan] DB {mb(size_before)} | wallet prune: "
          f"{plan['wallet_prune']['count']} ({prune_pct}%, "
          f"{plan['wallet_prune']['swap_rows']} swap rows) | "
          f"poin pool mati: {plan['price_points']['dead_pool_rows']:,} | "
          f"downsample: {plan['price_points']['downsample_rows']:,} poin "
          f"di {plan['price_points']['downsample_pools']} pool", flush=True)

    result: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "applied": do_apply,
        "size_before": size_before,
        "plan": {k: v for k, v in plan.items() if not k.startswith("_")},
    }
    if do_apply:
        if prune_pct > MAX_WALLET_PRUNE_PCT:
            sys.exit("ABORT: rencana prune melebihi batas sanity")
        done = apply(conn, plan)
        result["applied_detail"] = done
        print(f"[kerucutkan] apply: {done}", flush=True)
        print("[kerucutkan] VACUUM (bisa 1-2 menit)...", flush=True)
        t0 = time.time()
        conn.execute("vacuum")
        result["vacuum_s"] = round(time.time() - t0, 1)
        # kanonik ikut kepotong wallet yg diprune -> ekspor ulang + refresh
        try:
            import post_delta_reapply as pdr
            pdr.export_canonical(conn)
            print("[kerucutkan] JSON kanonik diekspor ulang", flush=True)
        except Exception as e:
            result["export_canonical"] = f"error: {str(e)[:120]}"
    conn.close()

    if do_apply:
        size_after = DB.stat().st_size
        result["size_after"] = size_after
        result["freed_bytes"] = size_before - size_after
        print(f"[kerucutkan] DB: {mb(size_before)} -> {mb(size_after)} "
              f"(hemat {mb(size_before - size_after)})", flush=True)
        import subprocess
        subprocess.run([sys.executable, "scripts/refresh_results_local.py"],
                       cwd=str(REPO))
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"[kerucutkan] laporan: {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
