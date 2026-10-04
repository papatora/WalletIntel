"""Monitor progress kerja otomatis: sweep queue [VPS] + arkham harvest [PC].

Loop tiap 10 menit, tulis log + status. Berhenti setelah max iterasi.
SSH ringan: 1 koneksi singkat per iterasi (aman utk sshd).
Jalankan: python scripts/monitor_cielo_sweep.py [iterasi=36] [interval_s=600]
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
LOG = REPO / "logs" / "cielo_monitor.log"


def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def vps_status(ssh) -> dict:
    _, o, _ = ssh.exec_command(
        "pgrep -fc 'volume_sweep.py' || true; "
        "cd /opt/topwallet && .venv/bin/python -c \""
        "import json,sqlite3;"
        "st=json.load(open('data/volume_sweep_state.json'));"
        "c=sqlite3.connect('file:data/topwallet.db?mode=ro',uri=True);"
        "q=lambda s:c.execute(s).fetchone()[0];"
        "print('queue',len(st.get('caQueue',[])));"
        "print('scores',q('select count(*) from wallet_scores'));"
        "print('maxts',q('select max(ts) from swap_events'));"
        "print('wallets',q('select count(*) from wallets'))\"", timeout=45)
    lines = o.read().decode(errors="replace").strip().splitlines()
    return {"sweep_proc": lines[0] if lines else "?",
            "queue": lines[1] if len(lines) > 1 else "?",
            "scores": lines[2] if len(lines) > 2 else "?",
            "maxts": lines[3] if len(lines) > 3 else "?",
            "wallets": lines[4] if len(lines) > 4 else "?"}


def main() -> int:
    iters = int(sys.argv[1]) if len(sys.argv) > 1 else 36
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 600
    from _vps import connect
    ark = REPO / "results" / "arkham_status.json"
    for i in range(iters):
        try:
            ssh = connect()
            st = vps_status(ssh)
            ssh.close()
            a = json.loads(ark.read_text(encoding="utf-8")) if ark.exists() else {}
            log(f"it={i+1}/{iters} VPS[sweep={st['sweep_proc']} queue={st['queue']} "
                f"scores={st['scores']} maxts={st['maxts']} wallets={st['wallets']}] "
                f"Arkham[checked={a.get('checked')} queue={a.get('queue')} phase={a.get('phase')}]")
        except Exception as e:
            log(f"it={i+1}/{iters} ERROR {str(e)[:120]}")
        time.sleep(interval)
    log("monitor selesai")
    return 0


if __name__ == "__main__":
    sys.exit(main())
