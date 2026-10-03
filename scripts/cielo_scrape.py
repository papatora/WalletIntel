"""Cielo public-lists harvester — via Brave CDP session (user's own browser).

Tidak pakai bypass apapun: fetch dibuat DARI halaman app.cielo.finance yang
terbuka di Brave milik user (pola sama dgn arkham flow, S-37-E).

Mode:
  python scripts/cielo_scrape.py lists     # semua metadata public lists (resumable)
  python scripts/cielo_scrape.py status    # ringkasan hasil

Output:
  results/cielo/cielo_lists.json    {id: {...list...}}
  results/cielo/scrape_state.json   {cursor, pages, updated_at}
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
STATE_FILE = OUT_DIR / "scrape_state.json"
CDP = "http://127.0.0.1:9222"
PAGE_URL = "https://app.cielo.finance/tracking?view=public-lists"

FETCH_JS = """
async (inp) => {
    const r = await fetch('/api/trpc/lists.getListsInfiniteScroll?batch=1&input=' +
        encodeURIComponent(JSON.stringify({"0": {"json": inp}})), {
        headers: {'trpc-accept': 'application/jsonl', 'x-trpc-source': 'nextjs-react',
                  'x-page-route': '/tracking'}
    });
    return {status: r.status, body: await r.text()};
}
"""


def load(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


def get_page(page, cursor: str, size: int = 50):
    inp = {"search": "", "order": "new", "followingOnly": False,
           "size": size, "cursor": cursor, "direction": "forward"}
    res = page.evaluate(FETCH_JS, inp)
    if res["status"] != 200:
        raise RuntimeError(f"HTTP {res['status']}")
    items, next_cursor = [], None
    for line in res["body"].strip().splitlines():
        j = json.loads(line)
        payload = j.get("json")
        if not isinstance(payload, list) or len(payload) < 3:
            continue
        for entry in payload[2]:
            inner = entry[0] if isinstance(entry, list) and entry else entry
            if isinstance(inner, dict) and inner.get("status") == "ok":
                data = inner.get("data") or []
                if isinstance(data, list):
                    items.extend(data)
                paging = inner.get("paging") or {}
                nq = paging.get("next_query") or ""
                if "after=" in nq:
                    after = nq.split("after=")[1]
                    next_cursor = after.split("&")[0]
    return items, next_cursor


def scrape_lists() -> int:
    from playwright.sync_api import sync_playwright

    lists = load(LISTS_FILE, {})
    state = load(STATE_FILE, {"cursor": "", "pages": 0})
    cursor = state.get("cursor", "")
    pages = state.get("pages", 0)

    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(CDP)
        ctx = b.contexts[0]
        page = None
        for pg in ctx.pages:
            if "app.cielo.finance" in pg.url:
                page = pg
                break
        if page is None:
            page = ctx.new_page()
            page.goto(PAGE_URL, timeout=60000)
            page.wait_for_timeout(5000)

        empty_streak = 0
        while True:
            items, next_cursor = get_page(page, cursor)
            pages += 1
            new = 0
            for it in items:
                lid = str(it.get("id"))
                if lid not in lists:
                    new += 1
                lists[lid] = it
            state.update({"cursor": cursor, "pages": pages,
                          "updated_at": datetime.now(timezone.utc).isoformat(),
                          "total": len(lists)})
            save(LISTS_FILE, lists)
            save(STATE_FILE, state)
            print(f"[page {pages}] items={len(items)} new={new} "
                  f"total={len(lists)} cursor={cursor!r} next={next_cursor!r}", flush=True)
            if not items or not next_cursor or next_cursor == cursor:
                empty_streak += 1
                if empty_streak >= 2 or not items:
                    break
            cursor = next_cursor
            time.sleep(1.2)

    print(f"SELESAI: {len(lists)} lists, {pages} halaman")
    return 0


def status() -> int:
    lists = load(LISTS_FILE, {})
    if not lists:
        print("belum ada data")
        return 0
    total_wallets = sum(l.get("wallets_count") or 0 for l in lists.values())
    rh = [l for l in lists.values()
          if "robinhood" in (l.get("name") or "").lower()
          or "robinhood" in (l.get("description") or "").lower()
          or (l.get("name") or "").lower() in ("track rh",)]
    print(f"lists: {len(lists)} | total wallets terdaftar: {total_wallets:,}")
    big = sorted(lists.values(), key=lambda l: l.get("wallets_count") or 0, reverse=True)[:10]
    print("terbesar:")
    for l in big:
        print(f"  {l.get('wallets_count'):>6} {l.get('name','')[:40]} id={l['id']}")
    print(f"RH-related: {len(rh)}")
    for l in rh[:15]:
        print(f"  {l.get('wallets_count'):>6} {l.get('name','')[:40]} id={l['id']}")
    return 0


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "lists"
    if mode == "lists":
        sys.exit(scrape_lists())
    elif mode == "status":
        sys.exit(status())
    else:
        print(__doc__)
        sys.exit(2)
