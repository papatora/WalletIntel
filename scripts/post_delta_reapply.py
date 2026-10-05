"""ORKESTRATOR pasca-delta (S-51h, temuan audit P1): jalankan SEMUA langkah
restore/re-apply setelah rebuild_local_db menimpa DB.

Latar: night_delta → rebuild_local_db MENIMPA DB lokal dgn dump VPS. Tabel
lokal-only (wallet_social, label POOL/NOISE/ACTIVE_MIN/DORMANT/CT) MUSNAH.
Script ini dipanggil night_delta otomatis dan idempoten:
  1. restore wallet_social dr results/social/wallet_social.json
  2. restore label lokal dr results/labels_local.json
  3. classify_local (detektor penuh, compute-only)
  4. classify_contracts_noise --mode all (eth_getCode + noise desc)
  5. apply_ct_attributed + dedupe_generalist
  6. ekspor ulang JSON kanonik
Dipanggil: python scripts/post_delta_reapply.py
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DB = REPO / "data" / "topwallet.db"
PY = sys.executable

SOCIAL_JSON = REPO / "results" / "social" / "wallet_social.json"
LABELS_JSON = REPO / "results" / "labels_local.json"

SOCIAL_SCHEMA = """create table if not exists wallet_social (
  address text not null, source text not null,
  twitter_username text, twitter_name text, twitter_fans integer,
  name text, tags text, extra text, updated_at text,
  primary key (address, source));"""
SOCIAL_COLS = ("address", "source", "twitter_username", "twitter_name",
               "twitter_fans", "name", "tags", "extra", "updated_at")


def step(msg: str) -> None:
    print(f"[reapply] {msg}", flush=True)


def restore_social(conn: sqlite3.Connection) -> int:
    if not SOCIAL_JSON.exists():
        step("social JSON tidak ada — skip restore")
        return 0
    doc = json.loads(SOCIAL_JSON.read_text(encoding="utf-8"))
    conn.execute(SOCIAL_SCHEMA)
    n = 0
    for r in doc.get("rows", []):
        conn.execute(
            """insert into wallet_social (address, source, twitter_username,
                 twitter_name, twitter_fans, name, tags, extra, updated_at)
               values (?,?,?,?,?,?,?,?,?)
               on conflict(address, source) do update set
                 twitter_username=excluded.twitter_username,
                 twitter_name=excluded.twitter_name,
                 twitter_fans=excluded.twitter_fans, name=excluded.name,
                 tags=excluded.tags, extra=excluded.extra,
                 updated_at=excluded.updated_at""",
            tuple(r.get(c) for c in SOCIAL_COLS))
        n += 1
    conn.commit()
    step(f"wallet_social restore: {n} rows")
    return n


def restore_labels(conn: sqlite3.Connection) -> int:
    if not LABELS_JSON.exists():
        step("labels JSON tidak ada — skip restore")
        return 0
    doc = json.loads(LABELS_JSON.read_text(encoding="utf-8"))
    n = 0
    for r in doc.get("labels", []):
        conn.execute(
            """insert into wallet_labels (wallet_address, label, confidence,
                 evidence, assigned_at)
               values (?,?,?,?,?)
               on conflict(wallet_address, label) do update set
                 confidence=excluded.confidence,
                 evidence=excluded.evidence,
                 assigned_at=excluded.assigned_at""",
            (r["address"], r["label"], r["confidence"], r["evidence"],
             r.get("assigned_at") or now_iso()))
        n += 1
    conn.commit()
    step(f"label lokal restore: {n} rows")
    return n


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(script: str, *args: str) -> None:
    step(f"jalankan {script} {' '.join(args)}")
    r = subprocess.run([PY, str(REPO / "scripts" / script), *args],
                       cwd=str(REPO), capture_output=True, text=True)
    tail = (r.stdout or "").strip().splitlines()[-3:]
    for ln in tail:
        print(f"  | {ln}", flush=True)
    if r.returncode != 0:
        print(f"  | STDERR {(r.stderr or '')[-300:]}", flush=True)


def export_canonical(conn: sqlite3.Connection) -> None:
    now = now_iso()
    LOCAL = ("POOL_CONTRACT", "NOISE", "ACTIVE_MIN", "DORMANT", "CT_ATTRIBUTED")
    rows = conn.execute(
        "select wallet_address, label, confidence, evidence from wallet_labels "
        "where label in (" + ",".join("?" * len(LOCAL)) + ")", LOCAL).fetchall()
    SOCIAL_JSON.parent.mkdir(parents=True, exist_ok=True)
    LABELS_JSON.parent.mkdir(parents=True, exist_ok=True)
    LABELS_JSON.write_text(json.dumps(
        {"updated_at": now, "labels": [dict(zip(("address", "label", "confidence", "evidence"), r)) for r in rows]},
        ensure_ascii=False, indent=1), encoding="utf-8")
    rows2 = conn.execute(
        "select address, source, twitter_username, twitter_name, twitter_fans, "
        "name, tags, extra, x_gmgn, x_arkham, x_conflict, x_primary, updated_at "
        "from wallet_social").fetchall()
    SOCIAL_JSON.write_text(json.dumps(
        {"updated_at": now, "rows": [dict(zip(
            ("address", "source", "twitter_username", "twitter_name", "twitter_fans",
             "name", "tags", "extra", "x_gmgn", "x_arkham", "x_conflict", "x_primary",
             "updated_at"), r)) for r in rows2]},
        ensure_ascii=False, indent=1), encoding="utf-8")
    step(f"JSON kanonik diekspor: {len(rows)} labels, {len(rows2)} social")


def main() -> int:
    conn = sqlite3.connect(DB, timeout=90)
    conn.execute("pragma busy_timeout=90000")

    # skema + kolom ekstra (delta bisa bawa DB tanpa tabel lokal)
    conn.execute(SOCIAL_SCHEMA)
    for a in ("x_gmgn", "x_arkham", "x_conflict", "x_primary"):
        try:
            conn.execute(f"alter table wallet_social add column {a} text")
        except sqlite3.OperationalError:
            pass
    conn.commit()

    restore_social(conn)
    restore_labels(conn)
    conn.close()

    run("classify_local.py")
    run("classify_contracts_noise.py", "--mode", "all",
        "--top-n", "2000", "--noise-limit", "400")
    run("apply_ct_attributed.py")
    run("dedupe_generalist.py")

    conn = sqlite3.connect(DB, timeout=90)
    conn.execute("pragma busy_timeout=90000")
    export_canonical(conn)
    conn.close()
    step("SELESAI — DB lokal kembali lengkap pasca-delta")
    return 0


if __name__ == "__main__":
    sys.exit(main())
