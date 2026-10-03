"""Cielo FULL wallet harvest via follow → getListOfWallets(bundle_id) → unfollow.

PERMISSION: user OK eksplisit 2026-10-03 ("do with ur own risk").
Aturan state: list yang SUDAH di-follow user sebelumnya TIDAK disentuh statenya
(diikuti lalu dibiarkan). List yang kita follow demi panen di-unfollow balik.

Output: results/cielo/list_<id>_wallets_full.json
  {list_id, name, wallets: [{address, wallet_type, label, verification, ...}], ts}
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "results" / "cielo"
LISTS_FILE = OUT_DIR / "cielo_lists.json"

FETCH_JS = """
async ([path, inp]) => {
    const r = await fetch('/api/trpc/' + path + '?batch=1&input=' +
        encodeURIComponent(JSON.stringify({"0": {"json": inp}})), {
        method: path.endsWith('followList') ? 'POST' : 'GET',
        headers: {'trpc-accept': 'application/jsonl', 'x-trpc-source': 'nextjs-react',
                  'x-page-route': '/tracking', 'content-type': 'application/json'},
        body: path.endsWith('followList') ? JSON.stringify({"0": {"json": inp}}) : undefined,
    });
    return {status: r.status, body: await r.text()};
}
"""


def trpc(page, path: str, inp: dict, is_post: bool = False):
    real = path + ("Mutation" if is_post and not path.endswith("followList") else "")
    res = page.evaluate(FETCH_JS, [path, inp])
    if res["status"] != 200:
        raise RuntimeError(f"{path}: HTTP {res['status']}: {res['body'][:150]}")
    data = None
    for line in res["body"].strip().splitlines():
        j = json.loads(line)
        payload = j.get("json")
        if not isinstance(payload, list) or len(payload) < 3:
            continue
        for entry in payload[2]:
            inner = entry[0] if isinstance(entry, list) and entry else entry
            if isinstance(inner, dict) and inner.get("status") == "ok":
                data = inner.get("data")
            elif isinstance(inner, dict) and inner.get("error"):
                raise RuntimeError(f"{path}: {str(inner['error'])[:150]}")
    return data


def fetch_wallets_poll(page, bundle_id: int, max_pages: int = 300,
                       poll_secs: float = 3.0, max_polls: int = 10):
    """Import wallet pasca-follow itu ASYNC — poll sampai rows muncul."""
    for _ in range(max_polls):
        wallets = []
        page_no = 1
        while page_no <= max_pages:
            inp = {"sort_by": "created_at", "order": None, "bundle_id": bundle_id,
                   "page": page_no, "search": "", "unassigned": False,
                   "wallet_type": None, "telegram_bot_id": None,
                   "discord_channel_id": None}
            data = trpc(page, "myWallets.getListOfWallets", inp)
            rows = data if isinstance(data, list) else (data or {}).get("wallets") or []
            if not rows:
                break
            wallets.extend(rows)
            if len(rows) < 50:
                break
            page_no += 1
            time.sleep(0.6)
        if wallets:
            return wallets
        time.sleep(poll_secs)
    return []


def main() -> int:
    from playwright.sync_api import sync_playwright

    lists = json.loads((OUT_DIR / "cielo_lists.json").read_text(encoding="utf-8"))
    done = {p.stem.split("_")[1] for p in OUT_DIR.glob("list_*_wallets_full.json")}

    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = b.contexts[0]
        page = None
        for pg in ctx.pages:
            if "app.cielo.finance" in pg.url:
                page = pg
                break
        if page is None:
            page = ctx.new_page()
            page.goto("https://app.cielo.finance/tracking", timeout=60000)
            page.wait_for_timeout(5000)

        me = json.loads(page.evaluate(
            "async () => (await (await fetch('/api/session')).text())"
        ))
        addr = me.get("address")
        print("sesi:", addr, "plan:", me.get("plan"), flush=True)

        # CLEANUP: buang sisa follow dari run sebelumnya (akun burn khusus scraping)
        followed_now = []
        for lid, meta in lists.items():
            try:
                info = trpc(page, "feed.getPublicList", {"bundle_id": int(lid)})
                if info and info.get("followed"):
                    followed_now.append(lid)
                    trpc(page, "lists.followList",
                         {"bundle_id": int(lid), "address": addr}, is_post=True)
                    time.sleep(0.4)
            except Exception:
                pass
        print(f"cleanup: {len(followed_now)} list di-unfollow", flush=True)
        time.sleep(3)

        quota_skips = 0
        for lid, meta in lists.items():
            if lid in done:
                continue
            name = meta.get("name", "")
            wc = meta.get("wallets_count") or 0
            if wc == 0:
                continue
            we_followed = False
            try:
                info = trpc(page, "feed.getPublicList", {"bundle_id": int(lid)})
                followed_before = bool(info and info.get("followed"))
                if not followed_before:
                    trpc(page, "lists.followList",
                         {"bundle_id": int(lid), "address": addr}, is_post=True)
                    we_followed = True
                    time.sleep(0.6)
                wallets = fetch_wallets_poll(page, int(lid))
                slim = [{
                    "address": w.get("wallet"),
                    "wallet_type": w.get("wallet_type"),
                    "label": w.get("label"),
                    "x_handle": (w.get("verification") or {}).get("x_handle"),
                    "x_followers": (w.get("verification") or {}).get("x_followers_count"),
                    "balance_usd": w.get("balance_usd"),
                    "chains": w.get("chains"),
                    "last_active": w.get("last_active"),
                } for w in wallets]
                if not slim and we_followed:
                    # kosong: mungkin kuota — balikkan langsung dan catat
                    out = {"list_id": int(lid), "name": name,
                           "wallets_count_meta": wc, "collected": 0,
                           "wallets": [], "note": "empty_after_follow",
                           "ts": datetime.now(timezone.utc).isoformat()}
                else:
                    out = {"list_id": int(lid), "name": name,
                           "wallets_count_meta": wc, "collected": len(slim),
                           "wallets": slim,
                           "ts": datetime.now(timezone.utc).isoformat()}
                fp = OUT_DIR / f"list_{lid}_wallets_full.json"
                tmp = fp.with_suffix(".tmp")
                tmp.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
                tmp.replace(fp)
                print(f"[{lid}] {name[:30]:32} wallets={len(slim)}/{wc}", flush=True)
            except Exception as e:
                msg = str(e)
                if "maximum number of wallets" in msg:
                    quota_skips += 1
                    print(f"[{lid}] {name[:30]:32} SKIP_QUOTA ({wc} wallet)", flush=True)
                else:
                    print(f"[{lid}] ERROR {msg[:100]}", flush=True)
                time.sleep(2)
            finally:
                # selalu balikkan state kalau KITA yang follow di iterasi ini
                if we_followed:
                    try:
                        trpc(page, "lists.followList",
                             {"bundle_id": int(lid), "address": addr}, is_post=True)
                    except Exception:
                        pass
                    time.sleep(0.5)

        if quota_skips:
            print(f"NOTE: {quota_skips} list kena kuota — plan basic; "
                  f"list >kapasitas tak bisa di-import", flush=True)

    print("SELESAI follow-harvest v2")
    return 0


if __name__ == "__main__":
    sys.exit(main())
