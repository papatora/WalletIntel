"""Tes live 2 proxy baru dari VPS (read-only)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _vps  # noqa: E402

REMOTE = r'''
P=$(sed -n 7p /opt/topwallet/proxies.txt)
echo "proxy7: ${P##*@}"
curl -s -m 15 -x "$P" https://api.ipify.org && echo " OK"
P2=$(sed -n 55p /opt/topwallet/proxies.txt)
echo "proxy55: ${P2##*@}"
curl -s -m 15 -x "$P2" https://api.ipify.org && echo " OK"
'''


def main() -> int:
    ssh = _vps.connect()
    _, out, err = ssh.exec_command(REMOTE, timeout=60)
    print(out.read().decode().strip()[:400])
    e = err.read().decode().strip()[:200]
    if e:
        print("ERR:", e)
    ssh.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
