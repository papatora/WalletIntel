import csv, os, tempfile

src = os.path.join(tempfile.gettempdir(), "proc_audit.csv")
rows = list(csv.DictReader(open(src, encoding="utf-8", errors="replace")))
print("TOTAL PROSES:", len(rows))
from collections import Counter
bycat = Counter()
flagged = []
for r in rows:
    name = (r.get("Name") or "").strip()
    path = (r.get("ExecutablePath") or "").strip()
    p = path.lower().replace("\\\\", "\\")
    if not path:
        bycat["(sistem, tanpa path)"] += 1
    elif "system32" in p or "syswow64" in p or "\\windows\\" in p:
        bycat["Windows/system"] += 1
    elif "program files" in p:
        bycat["Program Files"] += 1
    elif "appdata" in p:
        bycat["AppData"] += 1
        if "\\temp\\" in p:
            flagged.append((r["ProcessId"], name, path))
    elif "walletintel" in p:
        bycat["WalletIntel (kita)"] += 1
    else:
        bycat["Lainnya"] += 1
print("kategori:", dict(bycat))
print("proses dari Temp:", flagged if flagged else "0 (bersih)")
svc = [r for r in rows if r["Name"].lower() == "svchost.exe"
       and r["ExecutablePath"] and "system32" not in r["ExecutablePath"].lower()]
print("svchost di luar System32:", len(svc), [(r["ProcessId"], r["ExecutablePath"]) for r in svc][:3])
print()
print("=== PROSES dari AppData / lokasi lain (bukan Windows/Program Files):")
seen = set()
for r in rows:
    path = (r.get("ExecutablePath") or "")
    p = path.lower()
    if not path:
        continue
    if "appdata" in p or ("program files" not in p and "\\windows\\" not in p
                          and "system32" not in p and "system32" not in p):
        key = (r["Name"], path)
        if key in seen:
            continue
        seen.add(key)
        print(f"  {r['Name'][:36]:36s} {path[:96]}")
