"""Klasifikasi LOKAL (S-51f) — compute-only atas data lokal, tanpa network.

LATAR (pertanyaan user 2026-10-05): ACTIVE_MIN/GENERALIST menumpuk karena
classify_all_wallets hanya jalan di VPS saat stage analyze menuntaskan
export penuh — cycle analyze lambat/crash-retry sehingga wallet baru menumpuk
tanpa label. Dump delta membawa SEMUA data (bukan cuma harian), jadi kita
bisa mengklasifikasi di PC dengan DETEKTOR YANG SAMA (src.analyze.
wallet_classifier) atas swap_events lokal — compute murni, bukan scraping.

Output: wallet_labels (upsert label taksonomi; GENERALIST/ACTIVE_MIN/DORMANT
dihapus utk wallet yang kini punya label khusus). Label orthogonal lain
(CT_ATTRIBUTED/POOL_CONTRACT/NOISE/dll) tidak disentuh.

Pemakaian: python scripts/classify_local.py
"""
from __future__ import annotations

import json
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

DB = REPO / "data" / "topwallet.db"


class Ev(NamedTuple):
    wallet_address: str
    token_address: str
    block_num: int
    side: str
    token_amount: float
    usd_value: float | None
    tx_hash: str
    ts: str


def main() -> int:
    from src.analyze.wallet_classifier import (
        _airdrop_signal, _bundle_signal, _dev_signals, _insider_signal,
        _mev_signal, _sniper_signal, _cluster_signal, CONF,
    )

    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    print("memuat swap_events lokal...", flush=True)
    from datetime import datetime as _dt

    def _ts(v):
        if not v:
            return None
        try:
            return _dt.fromisoformat(str(v).replace(" ", "T"))
        except ValueError:
            return None

    by_wallet: dict[str, list[Ev]] = defaultdict(list)
    for wa, tok, blk, side, amt, usd, tx, ts in conn.execute(
        "select lower(wallet_address), lower(token_address), block_num, side, "
        "token_amount, usd_value, tx_hash, ts from swap_events "
        "order by block_num, id"
    ):
        by_wallet[wa].append(Ev(wa, tok, blk, side, amt, usd, tx, _ts(ts)))
    print(f"wallet dgn swap: {len(by_wallet)}", flush=True)

    token_pool = dict(conn.execute("select token_address, address from pools"))
    pool_first = dict(conn.execute(
        "select pool_address, min(block_num) from price_points group by pool_address"))
    conn.close()
    token_first = {tok: pool_first[pool] for tok, pool in token_pool.items()
                   if pool in pool_first}

    res = REPO / "results"
    forensics = _load(res / "funding_forensics.json", {})
    funding = {}
    for row in (forensics or {}).get("wallets", []):
        if isinstance(row, dict) and row.get("wallet"):
            funding[row["wallet"].lower()] = {
                "funder": ((row.get("funding") or {}).get("funder") or ""),
                "dev_fingerprint": row.get("dev_fingerprint") or {},
            }
    clusters_file = _load(res / "funder_clusters.json", None)
    ct_map = _ct_map(_load(res / "external_leaderboards.json", {}))

    print("menjalankan detektor...", flush=True)
    sig_bundle = _bundle_signal(by_wallet, token_first)
    sig_sniper = _sniper_signal(by_wallet, token_first)
    sig_insider = _insider_signal(by_wallet)
    sig_airdrop = _airdrop_signal(by_wallet)
    sig_serial, sig_dev = _dev_signals(by_wallet, token_first, funding)
    sig_mev = _mev_signal(by_wallet)
    # S-51h audit: score_cluster dari wallet_scores (parity dgn jalur VPS)
    _sc = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    score_cluster = dict(_sc.execute(
        "select lower(wallet_address), cluster_id from wallet_scores where cluster_id is not null"))
    _sc.close()
    sig_cluster = _cluster_signal(set(by_wallet), funding, clusters_file, score_cluster)

    # --- susun label per wallet (logika identik dgn classify_all_wallets) ---
    now = datetime.now(timezone.utc).isoformat()
    classified: dict[str, dict[str, tuple[float, dict]]] = {}
    for wallet in sorted(by_wallet):
        labels: dict[str, tuple[float, dict]] = {}

        def add(label: str, evidence: dict) -> None:
            labels.setdefault(label, (CONF[label], evidence))

        if wallet in sig_serial:
            add("DEV_SERIAL_RUGGER", sig_serial[wallet])
        elif wallet in sig_dev:
            add("DEV", sig_dev[wallet])
        if wallet in sig_bundle:
            add("BUNDLER_SUSPECT", sig_bundle[wallet])
        if wallet in sig_sniper:
            add("SNIPER", sig_sniper[wallet])
        if wallet in sig_insider:
            add("INSIDER", sig_insider[wallet])
        if wallet in sig_airdrop:
            add("AIRDROP_FARMER", sig_airdrop[wallet])
        if wallet in sig_mev:
            add("MEV_BOT", sig_mev[wallet])
        if wallet in ct_map:
            add("CT_ATTRIBUTED", ct_map[wallet])
        for lbl, conf, evd in sig_cluster.get(wallet, []):
            labels.setdefault(lbl, (conf, evd))
        if labels:
            classified[wallet] = labels

    from collections import Counter
    dist = Counter()
    for labels in classified.values():
        for lab in labels:
            dist[lab] += 1
    print("hasil detektor:", dict(dist.most_common(12)), flush=True)

    # --- tulis ke wallet_labels ------------------------------------------
    w = sqlite3.connect(DB, timeout=90)
    w.execute("pragma busy_timeout=90000")
    n_new = n_upgrade = 0
    for wallet, labels in classified.items():
        for lab, (conf, ev) in labels.items():
            cur = w.execute(
                "select confidence from wallet_labels where wallet_address=? and label=?",
                (wallet, lab)).fetchone()
            if cur is None:
                w.execute(
                    "insert into wallet_labels (wallet_address, label, confidence, evidence, assigned_at) "
                    "values (?,?,?,?,?)",
                    (wallet, lab, conf, json.dumps(ev, default=str)[:1500], now))
                n_new += 1
            elif (cur[0] or 0) < conf:
                w.execute(
                    "update wallet_labels set confidence=?, evidence=?, assigned_at=? "
                    "where wallet_address=? and label=?",
                    (conf, json.dumps(ev, default=str)[:1500], now, wallet, lab))
                n_upgrade += 1
    # GENERALIST/ACTIVE_MIN/DORMANT dihapus utk wallet yang kini berlabel khusus
    special = [k for k in classified]
    qmarks = ",".join("?" * len(special)) if special else "''"
    removed = 0
    for bucket in ("GENERALIST", "ACTIVE_MIN", "DORMANT"):
        cur = w.execute(
            f"delete from wallet_labels where label='{bucket}' and lower(wallet_address) in ({qmarks})",
            special)
        removed += cur.rowcount
    w.commit()
    dist2 = dict(w.execute(
        "select label, count(*) from wallet_labels group by label order by count(*) desc limit 14").fetchall())
    w.close()
    print(f"label baru: {n_new} | upgrade conf: {n_upgrade} | bucket sisa dihapus: {removed}")
    print("dist final:", dist2)
    return 0


def _load(path: Path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _ct_map(doc: dict) -> dict:
    # samakan dgn _ct_map classifier: wallet -> evidence utk CT_ATTRIBUTED
    try:
        from src.analyze.wallet_classifier import _ct_map as real
        return real(doc)
    except Exception:
        return {}


if __name__ == "__main__":
    sys.exit(main())
