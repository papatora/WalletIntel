"""One-shot ops (S-56): rotasi proxy Webshare di VPS + verifikasi.
Kredensial proxy dibaca dari file user (gitignored), TIDAK dikomit.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _vps  # noqa: E402

SRC = Path(r"C:\Users\ROG\Downloads\Telegram Desktop\Webshare 100 proxies.txt")


def main() -> int:
    rows = [l.strip() for l in SRC.read_text(encoding="utf-8", errors="replace").splitlines()
            if l.strip() and l.count(":") >= 3]
    print(f"proxy baru dari file user: {len(rows)}")
    # format file lama VPS = url http://user:pass@host:port (cek 1 baris dulu)
    ssh = _vps.connect()
    _, out, _ = ssh.exec_command("head -n 1 /opt/topwallet/proxies.txt | "
                                 "sed -E 's#//[^@]*@//#CRED@#'", timeout=20)
    old_fmt = out.read().decode().strip()
    print("format lama (disamarkan):", old_fmt)
    if old_fmt.startswith("http"):
        urls = [f"http://{u}:{p}@{h}:{pt}"
                for h, pt, u, p in (r.split(":", 3) for r in rows)]
        body = "\n".join(urls) + "\n"
    else:  # fallback: raw host:port:user:pass
        body = "\n".join(rows) + "\n"

    # tulis via sftp agar aman
    sftp = ssh.open_sftp()
    with sftp.open("/opt/topwallet/proxies.txt.new", "w") as f:
        f.write(body)
    sftp.close()
    _, out, err = ssh.exec_command(
        "mv /opt/topwallet/proxies.txt.new /opt/topwallet/proxies.txt && "
        "wc -l /opt/topwallet/proxies.txt && "
        "sed -n 1p /opt/topwallet/proxies.txt | sed -E 's#//[^@]*@//#CRED@#'",
        timeout=20)
    print(out.read().decode().strip())
    e = err.read().decode().strip()
    if e:
        print("ERR:", e[:200])
    ssh.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
