"""Tes kecepatan VPS→GitHub (upload 6MB ke release temp) — S-57c.
Skrip remote diupload via SFTP lalu dieksekusi (hindari jebakan quoting bash).
Release + tag langsung dihapus setelah tes.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _vps  # noqa: E402

REMOTE = r"""
set -e
cd /tmp
dd if=/dev/urandom of=st6mb.bin bs=1M count=6 2>/dev/null
TOK=$(grep ^GITHUB_TOKEN= /opt/topwallet/.env | cut -d= -f2)
T0=$(date +%s)
RID=$(curl -s -X POST \
  -H "Authorization: Bearer $TOK" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/papatora/WalletIntel/releases \
  -d '{"tag_name":"tmp-speedtest"}' | grep -o '"id": *[0-9]*' | head -1 | grep -o '[0-9]*')
U0=$(date +%s)
RES=$(curl -s -X POST \
  -H "Authorization: Bearer $TOK" \
  -H "Content-Type: application/octet-stream" \
  --data-binary @st6mb.bin \
  "https://uploads.github.com/repos/papatora/WalletIntel/releases/$RID/assets?name=st6mb.bin" \
  -o /dev/null -w '%{http_code} %{speed_upload}')
U1=$(date +%s)
echo "release_id=$RID create=$((U0-T0))s | upload 6MB: $RES B/s in $((U1-U0))s"
curl -s -X DELETE -H "Authorization: Bearer $TOK" \
  https://api.github.com/repos/papatora/WalletIntel/releases/$RID || true
git -C /opt/topwallet push origin --delete tmp-speedtest 2>/dev/null || true
rm -f st6mb.bin
"""


def main() -> int:
    ssh = _vps.connect()
    sftp = ssh.open_sftp()
    with sftp.open("/tmp/_speedtest_gh.sh", "w") as f:
        f.write(REMOTE)
    sftp.close()
    _, out, err = ssh.exec_command("bash /tmp/_speedtest_gh.sh; rm -f /tmp/_speedtest_gh.sh",
                                   timeout=240)
    print(out.read().decode().strip())
    e = err.read().decode().strip()[:300]
    if e:
        print("STDERR:", e)
    ssh.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
