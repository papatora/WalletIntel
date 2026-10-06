"""Merge hasil GMGN deep harvest (results/gmgn_web/deep/) ke JSON kanonik
wallet_social + laporan ringkas per wallet (rank terbaik, X handle, PnL).

Idempoten: merge by address, data rank terbaru menang utk kolom rank.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEEP = REPO / "results" / "gmgn_web" / "deep"
SOCIAL = REPO / "results" / "social" / "wallet_social.json"


def main() -> int:
    doc = json.loads(SOCIAL.read_text(encoding="utf-8"))
    rows = {r["address"] + "|" + r["source"]: r for r in doc["rows"]}
    added = updated = 0
    for p in sorted(DEEP.glob("deep_*_wallets.json")) or []:
        pass  # file per-tag lama; sumber sekarang deep_{chain}_{tag}_{period}.json
    for p in sorted(DEEP.glob("deep_*_*.json")):
        if p.name in ("deep_state.json",):
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            continue
        tag, period = d.get("tag"), d.get("period")
        for w in d.get("wallets", []):
            a = w["address"].lower()
            key = a + "|gmgn_rank"
            cur = rows.get(key)
            if cur is None:
                cur = {"address": a, "source": "gmgn_rank", "twitter_username": "",
                       "twitter_name": "", "twitter_fans": None, "name": "",
                       "tags": "[]", "extra": "{}", "updated_at": ""}
                rows[key] = cur
                added += 1
            if w.get("twitter_username") and not cur.get("twitter_username"):
                cur["twitter_username"] = w["twitter_username"]
            if w.get("twitter_name") and not cur.get("twitter_name"):
                cur["twitter_name"] = w["twitter_name"]
            tags = json.loads(cur.get("tags") or "[]")
            for t in w.get("tags") or []:
                if t not in tags:
                    tags.append(t)
            cur["tags"] = json.dumps(tags)
            ex = {"rank_tag": tag, "rank_period": period,
                  "pnl_30d": w.get("pnl_30d"), "winrate_30d": w.get("winrate_30d"),
                  "realized_profit_30d": w.get("realized_profit_30d"),
                  "volume_30d": w.get("volume_30d"), "txs_30d": w.get("txs_30d")}
            cur["extra"] = json.dumps(ex)
            cur["updated_at"] = datetime.now(timezone.utc).isoformat()
            updated += 1
    doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    SOCIAL.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    n_x = sum(1 for r in rows.values() if r.get("twitter_username"))
    print(f"merge deep: +{added} wallet baru, {updated} baris di-update, total {len(rows)} | X: {n_x}")
    return 0


if __name__ == "__main__":
    main()
