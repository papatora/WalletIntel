"""GMGN CopyTrade DEEP harvester — Rank wallets dengan cursor pagination.

S-51i: perluasan dari gmgn_web_rank.py — paginate cursor `after` sampai
habis (target per tag/period), sehingga bukan cuma 100 wallet pertama.

Endpoint (terverifikasi live):
  GET /api/v1/rank/{chain}/wallets/{period}?tag=T&after=CURSOR
    -> 100 wallet/call: twitter_username/name, tags, pnl/winrate/volume/txs
    -> paging.next_query utk cursor berikutnya

Output: results/gmgn_web/deep/{chain}_{tag}_{period}.json
State:  results/gmgn_web/deep_state.json (resumable per tag+period)
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "results" / "gmgn_web" / "deep"
CDP = "http://127.0.0.1:9222"

TAGS = ["smart_degen", "pump_smart", "kol", "dev", "renowned",
        "sniper", "fresh_wallet", "rat_trader"]
PERIODS = ["1d", "7d", "30d"]
PAGE_SLEEP = 1.2
MAX_PAGES_PER_TAG = 30  # 30 x 100 = 3000 wallet per tag/period

FETCH_JS = """
async (inp) => {
    const r = await fetch('/api/v1/rank/' + inp.chain + '/wallets/' + inp.period +
        '?tag=' + inp.tags.map(encodeURIComponent).join('&tag=') +
        (inp.cursor ? '&after=' + encodeURIComponent(inp.cursor) : ''), {
        headers: {'accept': 'application/json'}
    });
    return {status: r.status, body: await r.text()};
}
"""


def save_atomic(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)


def main() -> int:
    from playwright.sync_api import sync_playwright

    chain = sys.argv[1] if len(sys.argv) > 1 else "robinhood"
    OUT.mkdir(parents=True, exist_ok=True)
    state_p = OUT / "deep_state.json"
    state = json.loads(state_p.read_text(encoding="utf-8")) if state_p.exists() else {"done": []}

    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(CDP)
        ctx = b.contexts[0]
        page = None
        for pg in ctx.pages:
            if "gmgn.ai" in pg.url:
                page = pg
                break
        if page is None:
            page = ctx.new_page()
            page.goto(f"https://gmgn.ai/?chain={chain}", timeout=60000)
            page.wait_for_timeout(7000)

        grand_total = 0
        for tag in TAGS:
            for period in PERIODS:
                key = f"{chain}|{tag}|{period}"
                if key in state.get("done", []):
                    continue
                out_rows = []
                cursor = ""
                for page_i in range(MAX_PAGES_PER_TAG):
                    inp = {"chain": chain, "period": period, "tags": [tag], "cursor": cursor}
                    try:
                        res = page.evaluate(FETCH_JS, inp)
                    except Exception as e:
                        print(f"[{tag}/{period}] fetch err p{page_i}: {str(e)[:60]}", flush=True)
                        time.sleep(5)
                        continue
                    if res["status"] != 200:
                        print(f"[{tag}/{period}] HTTP {res['status']} — stop tag", flush=True)
                        break
                    try:
                        j = json.loads(res["body"])
                    except ValueError:
                        break
                    data = (j.get("data") or {})
                    rank = data.get("rank") or []
                    if not rank:
                        break
                    for w in rank:
                        addr = (w.get("wallet_address") or w.get("address") or "").lower()
                        if not addr:
                            continue
                        out_rows.append({
                            "address": addr,
                            "twitter_username": w.get("twitter_username") or "",
                            "twitter_name": w.get("twitter_name") or "",
                            "twitter_description": (w.get("twitter_description") or "")[:200],
                            "name": w.get("name") or "",
                            "tags": w.get("tags") or [],
                            "pnl_1d": w.get("pnl_1d"), "pnl_7d": w.get("pnl_7d"),
                            "pnl_30d": w.get("pnl_30d"),
                            "winrate_1d": w.get("winrate_1d"),
                            "winrate_7d": w.get("winrate_7d"),
                            "winrate_30d": w.get("winrate_30d"),
                            "realized_profit_7d": w.get("realized_profit_7d"),
                            "realized_profit_30d": w.get("realized_profit_30d"),
                            "volume_30d": w.get("volume_30d"),
                            "buy_30d": w.get("buy_30d"), "sell_30d": w.get("sell_30d"),
                            "txs_30d": w.get("txs_30d"),
                            "follow_count": w.get("follow_count"),
                            "last_active": w.get("last_active"),
                        })
                    paging = data.get("paging") or {}
                    nq = paging.get("next_query") or ""
                    if "after=" in nq:
                        cursor = nq.split("after=")[1].split("&")[0]
                    else:
                        break
                    time.sleep(PAGE_SLEEP)
                grand_total += len(out_rows)
                uniq = {r["address"]: r for r in out_rows}
                save_atomic(OUT / f"deep_{chain}_{tag}_{period}.json", {
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "tag": tag, "period": period,
                    "count": len(uniq), "wallets": list(uniq.values())})
                st = json.loads(state_p.read_text(encoding="utf-8")) if state_p.exists() else {"done": []}
                st.setdefault("done", []).append(key)
                st["updated_at"] = datetime.now(timezone.utc).isoformat()
                save = Path(state_p)
                tmp = save.with_suffix(".tmp")
                tmp.write_text(json.dumps(st, indent=1), encoding="utf-8")
                tmp.replace(save)
                print(f"[{tag}/{period}] wallets={len(uniq)}", flush=True)
                time.sleep(1.5)
        print(f"SELESAI deep harvest: total baris {grand_total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
