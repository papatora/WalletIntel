"""Cielo public-list WALLET harvester — scroll preview feed, kumpulkan /profile/<addr>.

Read-only terhadap akun Cielo user (tidak follow/unfollow apa pun).
Feed preview publik menampilkan tx per wallet di list dengan link
/profile/<full-address> — kita scroll sampai target tercapai/stagnan.

Resumable per list. Output: results/cielo/list_<id>_wallets.json
  {"list_id", "name", "wallets_count", "collected": [addr...], "coverage", "ts"}
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "results" / "cielo"
LISTS_FILE = OUT_DIR / "cielo_lists.json"
CDP = "http://127.0.0.1:9222"
PROFILE_RE = re.compile(r"^/(profile)/([0-9A-Za-z:_\-]{20,})$")

# list besar tak realistis di-scroll penuh; cap profil per list
MAX_PER_LIST = 500
MAX_SCROLL_ROUNDS = 60


def collect(page) -> set[str]:
    hrefs = page.evaluate(
        "() => [...document.querySelectorAll('a[href]')].map(a => a.getAttribute('href'))"
    )
    out = set()
    for h in hrefs or []:
        m = PROFILE_RE.match(h or "")
        if m:
            out.add(m.group(2))
    return out


def scrape_one(page, lid: str, meta: dict) -> dict:
    url = f"https://app.cielo.finance/feed/preview/{lid}"
    page.goto(url, timeout=60000)
    page.wait_for_timeout(6000)
    seen = collect(page)
    target = min(meta.get("wallets_count") or MAX_PER_LIST, MAX_PER_LIST)
    stale = 0
    for i in range(MAX_SCROLL_ROUNDS):
        if len(seen) >= target:
            break
        before = len(seen)
        page.evaluate("() => window.scrollBy(0, 4000)")
        page.wait_for_timeout(1800)
        seen = collect(page) | seen
        if len(seen) == before:
            stale += 1
            if stale >= 4:
                break
        else:
            stale = 0
    return {
        "list_id": int(lid),
        "name": meta.get("name", ""),
        "creator_name": meta.get("creator_name"),
        "twitter_handle": meta.get("twitter_handle"),
        "wallets_count": meta.get("wallets_count"),
        "collected": sorted(seen),
        "coverage": f"{len(seen)}/{meta.get('wallets_count')}",
        "ts": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    from playwright.sync_api import sync_playwright

    lists = json.loads(LISTS_FILE.read_text(encoding="utf-8"))
    # urutkan: list kecil dulu (cepat, coverage tinggi), besar belakangan
    order = sorted(lists.items(), key=lambda kv: kv[1].get("wallets_count") or 0)
    done_ids = {p.stem.split("_")[1] for p in OUT_DIR.glob("list_*_wallets.json")}

    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(CDP)
        ctx = b.contexts[0]
        page = ctx.new_page()
        for lid, meta in order:
            if lid in done_ids:
                continue
            wc = meta.get("wallets_count") or 0
            if wc == 0:
                continue
            try:
                res = scrape_one(page, lid, meta)
                out = OUT_DIR / f"list_{lid}_wallets.json"
                tmp = out.with_suffix(".tmp")
                tmp.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
                tmp.replace(out)
                print(f"[{lid}] {res['name'][:30]:32} {res['coverage']}", flush=True)
            except Exception as e:
                print(f"[{lid}] ERROR {str(e)[:100]}", flush=True)
                time.sleep(5)
            time.sleep(1.0)
        page.close()
    print("SELESAI semua list")
    return 0


if __name__ == "__main__":
    sys.exit(main())
