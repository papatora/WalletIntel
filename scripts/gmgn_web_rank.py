"""GMGN CopyTrade rank harvester — via Brave CDP (halaman gmgn.ai hidup).

Endpoint web (tanpa login, terverifikasi 2026-10-04):
  GET /api/v1/rank/{chain}/wallets/{period}?tag=X[&tag=Y]   → 100 wallet:
      twitter_username, twitter_name, tags, pnl/winrate 1d/7d/30d, volume, txs...
  GET /api/v1/notification/callout/rank                     → TopCallers:
      twitter_username, avg_multiplier, total_calls, top_tokens, follower_count

Grid: TAGS × PERIODS. Output: results/gmgn_web/
  rank_<chain>_<tag>_<period>.json  (mentah)
  gmgn_rank_social.json             (merge: address → profil sosial + rank meta)
  callout_rank.json                 (mentah callers)
Pemakaian: python scripts/gmgn_web_rank.py [chain=robinhood]
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "results" / "gmgn_web"
CDP = "http://127.0.0.1:9222"

TAGS = ["smart_degen", "pump_smart", "kol", "dev", "renowned", "fresh_wallet"]
PERIODS = ["1d", "7d", "30d"]

FETCH_JS = """
async (path) => {
    const r = await fetch(path, {headers: {'accept': 'application/json'}});
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
    social: dict[str, dict] = {}
    social_path = OUT / "gmgn_rank_social.json"
    if social_path.exists():
        social = json.loads(social_path.read_text(encoding="utf-8"))

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

        n_req = 0
        for tag in TAGS:
            for period in PERIODS:
                path = f"/api/v1/rank/{chain}/wallets/{period}?tag={tag}"
                try:
                    res = page.evaluate(FETCH_JS, path)
                    n_req += 1
                except Exception as e:
                    print(f"[{tag}/{period}] fetch err {str(e)[:70]}", flush=True)
                    continue
                if res["status"] != 200:
                    print(f"[{tag}/{period}] HTTP {res['status']}", flush=True)
                    time.sleep(2)
                    continue
                try:
                    j = json.loads(res["body"])
                except ValueError:
                    print(f"[{tag}/{period}] body bukan JSON (len {len(res['body'])})", flush=True)
                    time.sleep(2)
                    continue
                data = j.get("data") or {}
                rank = data.get("rank") or []
                slim = []
                for w in rank:
                    addr = (w.get("wallet_address") or w.get("address") or "").lower()
                    if not addr:
                        continue
                    slim.append({
                        "address": addr,
                        "twitter_username": w.get("twitter_username") or "",
                        "twitter_name": w.get("twitter_name") or "",
                        "name": w.get("name") or "",
                        "nickname": w.get("nickname") or "",
                        "tags": w.get("tags") or [],
                        "pnl_7d": w.get("pnl_7d"), "pnl_30d": w.get("pnl_30d"),
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
                save_atomic(OUT / f"rank_{chain}_{tag}_{period}.json",
                            {"updated_at": datetime.now(timezone.utc).isoformat(),
                             "endpoint": path, "count": len(slim), "rank": slim})
                # merge ke social map (list rank-meta per sumber)
                for s in slim:
                    ent = social.setdefault(s["address"], {
                        "address": s["address"],
                        "twitter_username": s["twitter_username"],
                        "twitter_name": s["twitter_name"],
                        "name": s["name"], "nickname": s["nickname"],
                        "tags": [], "sources": [],
                    })
                    if s["twitter_username"] and not ent["twitter_username"]:
                        ent["twitter_username"] = s["twitter_username"]
                        ent["twitter_name"] = s["twitter_name"]
                    for t in s["tags"]:
                        if t not in ent["tags"]:
                            ent["tags"].append(t)
                    if f"{tag}:{period}" not in ent["sources"]: ent["sources"].append(f"{tag}:{period}")
                    for k in ("pnl_30d", "winrate_30d", "realized_profit_30d",
                              "volume_30d", "txs_30d", "follow_count", "last_active"):
                        if s.get(k) is not None:
                            ent[k] = s.get(k)
                print(f"[{tag}/{period}] wallets={len(slim)}", flush=True)
                time.sleep(1.5)

        # callout rank (TopCallers)
        try:
            res = page.evaluate(FETCH_JS, "/api/v1/notification/callout/rank")
            if res["status"] == 200:
                j = json.loads(res["body"])
                d = j.get("data") or {}
                items = next((v for v in d.values() if isinstance(v, list)), [])
                save_atomic(OUT / "callout_rank.json", {
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "count": len(items), "items": items})
                for it in items:
                    addr = (it.get("wallet") or "").lower()
                    if not addr:
                        continue
                    ent = social.setdefault(addr, {
                        "address": addr, "twitter_username": "",
                        "twitter_name": "", "name": "", "nickname": "",
                        "tags": [], "sources": []})
                    if it.get("twitter_username"):
                        ent["twitter_username"] = it["twitter_username"]
                        ent["twitter_name"] = it.get("twitter_name") or ""
                    if "caller" not in ent["tags"]:
                        ent["tags"].append("caller")
                    ent["sources"].append("callout")
                    ent["caller_avg_multiplier"] = it.get("avg_multiplier")
                    ent["caller_total_calls"] = it.get("total_calls")
                    ent["caller_hit_2x"] = it.get("hit_2x_count")
                    ent["caller_follower_count"] = it.get("follower_count")
                print(f"[callout] callers={len(items)}", flush=True)
        except Exception as e:
            print(f"[callout] err {str(e)[:80]}", flush=True)

    social_doc = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "chain": chain, "n_requests": n_req,
        "profiles": social,
    }
    save_atomic(social_path, social_doc)
    n_tw = sum(1 for v in social.values() if v.get("twitter_username"))
    print(f"TOTAL: {len(social)} profil unik, {n_tw} punya X handle")
    return 0


if __name__ == "__main__":
    sys.exit(main())
