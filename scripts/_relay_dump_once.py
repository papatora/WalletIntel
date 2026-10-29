"""RELAY DUMP VIA GITHUB (S-57c) — delta transfer saat SFTP VPS→PC dicap
~7 KB/koneksi (bandwidth pasca-recovery jelek) sementara VPS→GitHub 3,3 MB/s.

Alur:
  1. VPS: tar seluruh local_snapshot.sql.part* → upload SATU asset ke release
     temp (tag relay-<fp>). Repo public => download lokal TANPA auth.
  2. Lokal: download asset via curl → extract part ke data/ → jalankan rantai
     rebuild lengkap (rebuild_local_db → post_delta_reapply → kerucutkan →
     refresh) + update night_state.json — replika night_delta pasca-fetch.
  3. Hapus release setelah sukses.

Pemakaian:
  python scripts/_relay_dump_once.py upload     # jalur 1 (VPS side)
  python scripts/_relay_dump_once.py local      # jalur 2+3 (PC side)
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _vps  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"
# tag HARUS sama antara run upload & local — default date-only (stabil
# seharian); run kedua sehari: upload menghapus release lama dulu.
TAG = sys.argv[2] if len(sys.argv) > 2 else time.strftime("relay-%Y%m%d")
ASSET = "dump.tar"
GH_API = "https://api.github.com/repos/papatora/WalletIntel"

UPLOAD_SH = r"""
set -e
cd /opt/topwallet/data
N=$(ls local_snapshot.sql.part* | wc -l)
echo "parts di VPS: $N"
tar cf /tmp/relay.tar local_snapshot.sql.part*
ls -la /tmp/relay.tar
TOK=$(grep ^GITHUB_TOKEN= /opt/topwallet/.env | cut -d= -f2)
# idempoten: hapus release + ref bertag sama bila ada (rerun seharian)
OLD=$(curl -s -H "Authorization: Bearer $TOK" https://api.github.com/repos/papatora/WalletIntel/releases/tags/TAGNAME | grep -o '"id": *[0-9]*' | head -1 | grep -o '[0-9]*')
if [ -n "$OLD" ] && [ "$OLD" != "1" ]; then
  curl -s -X DELETE -H "Authorization: Bearer $TOK" https://api.github.com/repos/papatora/WalletIntel/releases/$OLD || true
  git -C /opt/topwallet push origin --delete TAGNAME 2>/dev/null || true
fi
RID=$(curl -s -X POST -H "Authorization: Bearer $TOK" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/papatora/WalletIntel/releases \
  -d '{"tag_name":"TAGNAME"}' | grep -o '"id": *[0-9]*' | head -1 | grep -o '[0-9]*')
if [ -z "$RID" ]; then echo "release create gagal"; exit 1; fi
echo "release_id=$RID"
T0=$(date +%s)
RES=$(curl -s -X POST -H "Authorization: Bearer $TOK" \
  -H "Content-Type: application/x-tar" \
  --data-binary @/tmp/relay.tar \
  "https://uploads.github.com/repos/papatora/WalletIntel/releases/$RID/assets?name=ASSETNAME" \
  -o /dev/null -w '%{http_code} %{speed_upload}')
T1=$(date +%s)
echo "upload: $RES B/s in $((T1-T0))s"
rm -f /tmp/relay.tar
echo "RID=$RID" > /tmp/relay_rid
"""


def sh(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    print("$", " ".join(cmd[:6]), "...", flush=True)
    return subprocess.run(cmd, **kw)


def upload() -> int:
    ssh = _vps.connect()
    sftp = ssh.open_sftp()
    with sftp.open("/tmp/_relay_upload.sh", "w") as f:
        f.write(UPLOAD_SH.replace("TAGNAME", TAG).replace("ASSETNAME", ASSET))
    sftp.close()
    _, out, err = ssh.exec_command("bash /tmp/_relay_upload.sh; rm -f /tmp/_relay_upload.sh",
                                   timeout=1800)
    print(out.read().decode().strip())
    e = err.read().decode().strip()[:300]
    if e:
        print("STDERR:", e)
    ssh.close()
    return 0


def local() -> int:
    url = f"https://github.com/papatora/WalletIntel/releases/download/{TAG}/{ASSET}"
    tar = DATA / ASSET
    print(f"download {url}")
    r = sh(["curl", "-L", "--retry", "5", "-C", "-", "-o", str(tar), url],
           cwd=str(REPO))
    if r.returncode != 0 or not tar.exists():
        sys.exit("download gagal")
    print(f"tar: {tar.stat().st_size/1e6:.0f} MB")
    # extract part (timpa identik — part lama dari fp sama)
    r = sh(["tar", "xf", str(tar), "-C", str(DATA)])
    if r.returncode != 0:
        sys.exit("extract gagal")
    parts = sorted(DATA.glob("local_snapshot.sql.part*"))
    print(f"part lokal: {len(parts)}")
    if len(parts) < 50:
        sys.exit("part kurang dari 50 — extract tidak lengkap")

    # rantai rebuild (replika night_delta pasca-fetch)
    for step, timeout_s in [("rebuild_local_db.py", 30 * 60),
                            ("post_delta_reapply.py", 60 * 60),
                            ("kerucutkan.py --apply", 60 * 60),
                            ("refresh_results_local.py", 10 * 60)]:
        script, *args = step.split()
        rc = sh([sys.executable, f"scripts/{script}", *args], cwd=str(REPO)).returncode
        if rc != 0:
            print(f"!! {script} exit {rc} — lanjut manual")
            break

    # night_state
    import sqlite3
    con = sqlite3.connect(f"file:{DATA / 'topwallet.db'}?mode=ro", uri=True)
    wallets = con.execute("select count(*) from wallets").fetchone()[0]
    swaps = con.execute("select count(*) from swap_events").fetchone()[0]
    max_ts = str(con.execute("select max(ts) from swap_events").fetchone()[0])
    scores = con.execute("select count(*) from wallet_scores").fetchone()[0]
    con.close()
    st_path = REPO / "results" / "night_state.json"
    st = json.loads(st_path.read_text())
    st.update({"delta_status": "done", "delta_done": True, "wallets": wallets,
               "swaps": swaps, "swap_max_ts": max_ts, "wallet_scores": scores,
               "delta_finished_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
               "transport": f"github-relay ({TAG})"})
    st_path.write_text(json.dumps(st, indent=1))
    print(f"night_state: wallets={wallets} swaps={swaps} max_ts={max_ts} scores={scores}")

    # hapus release (asset + tag) via API lokal (PAT di .env)
    tok = ""
    for line in (REPO / ".env").read_text().splitlines():
        if line.startswith("GITHUB_TOKEN="):
            tok = line.split("=", 1)[1].strip()
    if tok:
        import urllib.request
        req = urllib.request.Request(f"{GH_API}/releases/tags/{TAG}",
                                     headers={"Authorization": f"Bearer {tok}"})
        with urllib.request.urlopen(req) as r:
            rid = json.load(r)["id"]
        dreq = urllib.request.Request(f"{GH_API}/releases/{rid}", method="DELETE",
                                      headers={"Authorization": f"Bearer {tok}"})
        urllib.request.urlopen(dreq)
        dreq2 = urllib.request.Request(f"{GH_API}/git/refs/tags/{TAG}", method="DELETE",
                                       headers={"Authorization": f"Bearer {tok}"})
        urllib.request.urlopen(dreq2)
        print("release + tag relay dihapus")
    tar.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "upload":
        sys.exit(upload())
    if mode == "local":
        sys.exit(local())
    print(__doc__)
    sys.exit(2)
