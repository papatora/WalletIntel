"""Verifikasi on-chain wallet-wallet dari Cielo public lists.

Sumber cek (jujur-jujur, tanpa halu):
  1. DB lokal        — wallet sudah dikenal? label apa? skor?
  2. Etherscan V2    — aktif di Robinhood chain? (chainid 4663, robinscan)
  3. Arkham (lokal)  — sudah berlabel entity?
  4. GMGN OpenAPI    — win rate/PnL 30d (throttle sopan)

Output: results/cielo/verify_results.json
  per wallet: {addr, lists[], addr_class, in_db, db_labels, db_score,
               rh_txcount, is_contract, arkham, gmgn, verdict}

Nametag rule (permintaan user 2026-10-03):
  nama = label Arkham jika ada; kalau tidak, pakai nama list Cielo
  dengan penanda "(*cielo)" — selalu provenance terbuka.
"""
from __future__ import annotations

import json
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

OUT_DIR = REPO / "results" / "cielo"
EVM_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
SOL_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


def load_wallets() -> dict[str, list[dict]]:
    """addr -> [{list_id, name, coverage, ts}]"""
    mapping: dict[str, list[dict]] = defaultdict(list)
    for p in sorted(OUT_DIR.glob("list_*_wallets.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        for a in d.get("collected", []):
            mapping[a].append({
                "list_id": d["list_id"], "name": d.get("name", ""),
                "coverage": d.get("coverage"), "ts": d.get("ts"),
            })
    return dict(mapping)


def addr_class(addr: str) -> str:
    if EVM_RE.match(addr):
        return "evm"
    if SOL_RE.match(addr):
        return "solana"
    return "other"


def check_db(evm_addrs: list[str]) -> dict[str, dict]:
    import sqlite3
    c = sqlite3.connect(f"file:{REPO / 'data' / 'topwallet.db'}?mode=ro", uri=True)
    out: dict[str, dict] = {}
    BATCH = 400
    for i in range(0, len(evm_addrs), BATCH):
        chunk = evm_addrs[i:i + BATCH]
        q = ",".join("?" * len(chunk))
        low = {a.lower(): a for a in chunk}
        rows = c.execute(
            f"select address, status, first_seen from wallets where lower(address) in ({q})",
            [a.lower() for a in chunk]).fetchall()
        for wa, status, first_seen in rows:
            out[low.get(wa.lower(), wa)] = {"in_db": True, "db_status": status, "db_first_seen": first_seen}
        # labels (ada di wallet_labels table: wallet_address, label, confidence?)
        try:
            rows = c.execute(
                f"select wallet_address, label from wallet_labels where lower(wallet_address) in ({q})",
                [a.lower() for a in chunk]).fetchall()
        except Exception:
            rows = []
        byw: dict[str, list[str]] = defaultdict(list)
        for wa, label in rows:
            byw[wa.lower()].append(label)
        for a in chunk:
            d = out.setdefault(low.get(a.lower(), a), {"in_db": False})
            labs = byw.get(a.lower())
            if labs:
                d["db_labels"] = labs
    c.close()
    return out


def check_etherscan(evm_addrs: list[str]) -> dict[str, dict]:
    """Aktif di Robinhood chain? (robinscan = Etherscan V2 chainid 4663).
    max_pages=1 per wallet — cukup untuk verdict aktif/tidak."""
    import asyncio
    from src.utils.etherscan_client import make_explorer_client

    async def run() -> dict[str, dict]:
        cli = make_explorer_client()
        out: dict[str, dict] = {}
        try:
            for i, a in enumerate(evm_addrs):
                try:
                    txs = await cli.address_transactions(a, max_pages=1)
                    d = {"rh_active": bool(txs)}
                    if txs:
                        first = txs[0]
                        d["rh_last_tx_block"] = first.get("block_number") or first.get("block")
                    out[a] = d
                except Exception as e:
                    out[a] = {"rh_error": str(e)[:120]}
                if (i + 1) % 25 == 0:
                    print(f"  etherscan {i + 1}/{len(evm_addrs)}", flush=True)
                await asyncio.sleep(0.15)
        finally:
            await cli.close()
        return out

    return asyncio.run(run())


def check_gmgn(evm_addrs: list[str]) -> dict[str, dict]:
    """Win rate/PnL 30d via GMGN (throttle sopan, public key)."""
    from src.discover.gmgn_client import GmgnClient
    cli = GmgnClient()
    out: dict[str, dict] = {}
    try:
        for i, a in enumerate(evm_addrs):
            try:
                st = cli.wallet_stats("robinhood", a, period="30d")
                if st:
                    out[a] = {
                        "gmgn_pnl_30d": st.get("pnl") or st.get("realized_profit"),
                        "gmgn_winrate_30d": st.get("win_rate"),
                        "gmgn_raw": {k: st.get(k) for k in list(st)[:6]},
                    }
                else:
                    out[a] = {"gmgn": None}
            except Exception as e:
                out[a] = {"gmgn_error": str(e)[:100]}
            if (i + 1) % 10 == 0:
                print(f"  gmgn {i + 1}/{len(evm_addrs)}", flush=True)
            time.sleep(0.6)
    finally:
        cli.close()
    return out


def build_nametags(results: dict[str, dict]) -> dict[str, dict]:
    """Nama tampil: Arkham label jika ada; kalau tidak, '<ListName> (*cielo)'.
    Wallet di banyak list: gabung nama list unik, batasi 2."""
    from collections import Counter
    tags: dict[str, dict] = {}
    for a, d in results.items():
        if d.get("addr_class") != "evm":
            continue
        arkham = d.get("arkham") or {}
        base = arkham.get("entity")
        src = "arkham"
        if not base:
            names = []
            for l in d.get("lists", []):
                n = (l.get("name") or "").strip()
                if n and n not in names:
                    names.append(n)
            if names:
                base = " / ".join(names[:2])
                src = "cielo"
        if not base:
            continue
        label = base if src == "arkham" else f"{base} (*cielo)"
        tags[a.lower()] = {
            "name": label, "source": src,
            "lists": [l["name"] for l in d.get("lists", [])],
            "verdict": d.get("verdict"),
        }
    return tags


def main() -> int:
    mapping = load_wallets()
    print(f"wallet unik dari lists: {len(mapping)}")
    classes = defaultdict(int)
    for a in mapping:
        classes[addr_class(a)] += 1
    print("kelas address:", dict(classes))

    evm = [a for a in mapping if addr_class(a) == "evm"]
    sol = [a for a in mapping if addr_class(a) == "solana"]

    results: dict[str, dict] = {}
    for a, lists in mapping.items():
        results[a] = {
            "addr_class": addr_class(a), "lists": lists,
            "first_list": lists[0]["name"] if lists else "",
        }

    if evm:
        db = check_db(evm)
        for a, d in db.items():
            results[a].update(d)
        n_db = sum(1 for a in evm if results[a].get("in_db"))
        print(f"EVM: {n_db}/{len(evm)} sudah ada di DB lokal")

    stage = sys.argv[1] if len(sys.argv) > 1 else "db"
    prev_path = OUT_DIR / "verify_results.json"
    prev = json.loads(prev_path.read_text(encoding="utf-8"))["results"] if prev_path.exists() else {}

    if stage in ("etherscan", "full") and evm:
        es = check_etherscan(evm)
        for a, d in es.items():
            results[a].update(d)
        n_act = sum(1 for a in evm if results[a].get("rh_active"))
        print(f"EVM aktif di robinhood chain: {n_act}/{len(evm)}")

    if stage in ("gmgn", "full") and evm:
        gm = check_gmgn(evm)
        for a, d in gm.items():
            results[a].update(d)

    # arkham lookup lokal
    ark_path = REPO / "results" / "arkham_entities.json"
    if ark_path.exists():
        ark = json.loads(ark_path.read_text(encoding="utf-8"))
        hit = 0
        for a in results:
            v = ark.get(a) or ark.get(a.lower())
            if isinstance(v, dict) and (v.get("entity") or v.get("name")):
                results[a]["arkham"] = {"entity": v.get("entity") or v.get("name")}
                hit += 1
        print(f"arkham lookup: {hit} wallet berlabel")

    # verdict jujur
    for a, d in results.items():
        if d.get("addr_class") != "evm":
            d["verdict"] = d["addr_class"].upper()
        elif d.get("in_db"):
            d["verdict"] = "KNOWN_IN_DB"
        elif d.get("rh_active"):
            d["verdict"] = "ROBINHOOD_ACTIVE"
        elif d.get("rh_error"):
            d["verdict"] = "CHECK_FAILED"
        else:
            d["verdict"] = "NOT_ON_ROBINHOOD"

    # nametag + merge hasil lama (resume-safe)
    for a, d in prev.items():
        if a not in results:
            results[a] = d
    tags = build_nametags(results)

    (OUT_DIR / "verify_results.json").write_text(
        json.dumps({
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "totals": {"all": len(results), "evm": len(evm), "solana": len(sol)},
            "results": results,
        }, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT_DIR / "nametags.json").write_text(
        json.dumps(tags, ensure_ascii=False, indent=1), encoding="utf-8")
    verdicts = Counter(d.get("verdict") for d in results.values())
    print("verdicts:", dict(verdicts))
    print(f"nametags: {len(tags)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
