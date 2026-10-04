"""Shutdown watcher — tunggu flag SHUTDOWN_READY lalu matikan PC.

Usage: python scripts/shutdown_watcher.py [max_hours=6] [countdown_s=120]

Kondisi:
  - results/SHUTDOWN_READY.flag ada -> commit/push/memory sudah selesai:
    hapus flag, shutdown dengan countdown (biar ZCode sempat tulis log terakhir).
  - timeout max_hours -> shutdown juga (status timeout dicatat).
Batal: buat file results/SHUTDOWN_ABORT.flag sebelum countdown habis.
"""
from __future__ import annotations

import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
READY = REPO / "results" / "SHUTDOWN_READY.flag"
ABORT = REPO / "results" / "SHUTDOWN_ABORT.flag"
LOG = REPO / "logs" / "shutdown_watcher.log"


def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def shutdown(countdown: int, why: str) -> None:
    if ABORT.exists():
        ABORT.unlink()
        log("ABORT ditemukan — shutdown dibatalkan")
        return
    log(f"SHUTDOWN ({why}) dalam {countdown}s")
    subprocess.run(
        ["shutdown", "/s", "/t", str(countdown),
         "/c", f"WalletIntel watcher: {why}. Simpan pekerjaanmu!"],
        check=False)


def main() -> int:
    max_hours = float(sys.argv[1]) if len(sys.argv) > 1 else 6.0
    countdown = int(sys.argv[2]) if len(sys.argv) > 2 else 120
    deadline = time.time() + max_hours * 3600
    log(f"watcher mulai: menunggu {READY.name} (maks {max_hours} jam)")
    while time.time() < deadline:
        if READY.exists():
            READY.unlink()
            time.sleep(90)  # beri ZCode waktu menulis log/commit terakhir
            shutdown(countdown, "semua pekerjaan selesai & ter-push")
            return 0
        time.sleep(30)
    shutdown(60, f"timeout {max_hours} jam tercapai — matikan paksa sesuai instruksi")
    return 0


if __name__ == "__main__":
    sys.exit(main())
