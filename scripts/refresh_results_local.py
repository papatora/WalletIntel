"""Refresh results/ dari DB lokal — menutup gap antara snapshot extract (VPS)
dan DB lokal hasil night_delta.

Yang diregenerasi:
  results/wallet_labels.json      <- tabel wallet_labels (derive_primary
                                     memakai PRIMARY_PRIORITY classifier yang sama)
  results/top_wallets_latest.json <- tabel wallet_scores
  results/top_wallets_latest.csv  <- versi CSV

Yang TIDAK bisa diregenerasi lokal (produk stage analyze penuh, bukan dump):
  wallet_pool.json, whale_entry_maps.json — biarkan snapshot VPS; catat di file.

Pemakaian: python scripts/refresh_results_local.py   (read-only thd DB)
"""
from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.analyze.wallet_classifier import PRIMARY_PRIORITY  # noqa: E402

DB = REPO / "data" / "topwallet.db"
OUT = REPO / "results"


def derive_primary(labels: list[str]) -> str:
    setl = set(labels)
    for prio in PRIMARY_PRIORITY:
        if prio in setl:
            return prio
    return labels[0] if labels else "UNCLASSIFIED"


def refresh_wallet_labels() -> dict:
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = c.execute(
        "select wallet_address, label, confidence, evidence from wallet_labels"
    ).fetchall()
    c.close()
    wallets: dict[str, dict] = {}
    for wa, label, conf, evidence in rows:
        e = wallets.setdefault(wa, {"labels": [], "conf": {}, "ev": {}})
        e["labels"].append(label)
        try:
            e["conf"][label] = float(conf) if conf is not None else 0.5
        except (TypeError, ValueError):
            e["conf"][label] = 0.5
        if evidence:
            try:
                e["ev"][label] = json.loads(evidence) if isinstance(evidence, str) else evidence
            except (ValueError, TypeError):
                e["ev"][label] = {"note": str(evidence)[:200]}
    out = {}
    for wa, e in wallets.items():
        labels = sorted(set(e["labels"]))
        primary = derive_primary(labels)
        out[wa.lower()] = {
            "primary_type": primary,
            "labels": labels,
            "evidence": e["ev"],
            "confidence": e["conf"],
        }
    doc = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "taxonomy": "docs/WALLET_TAXONOMY.md (14 types; primary = priority 1→14)",
        "source": "regenerated locally from data/topwallet.db (refresh_results_local.py)",
        "summary": {
            "wallets_classified": len(out),
            "label_rows": len(rows),
            "primary_types": dict(sorted(Counter(
                v["primary_type"] for v in out.values()).items())),
        },
        "wallets": out,
        "tag_overrides_applied": None,
        "_note": "tag_overrides merge dilakukan di jalur extract_wallets VPS; "
                 "nilai overrides sudah terwakili di label table hasil apply.",
    }
    (OUT / "wallet_labels.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    return doc["summary"]


def refresh_top_wallets() -> dict:
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = c.execute(
        "select wallet_address, computed_at, composite_score, metrics, "
        "trading_style, risk_flags, cluster_id from wallet_scores "
        "order by composite_score desc"
    ).fetchall()
    c.close()

    def parse(x, default):
        if not x:
            return default
        try:
            return json.loads(x)
        except (ValueError, TypeError):
            return default

    wallets = []
    for rank, (wa, computed_at, score, metrics, style, risk, cluster) in enumerate(rows, 1):
        wallets.append({
            "rank": rank,
            "wallet_address": wa,
            "composite_score": score,
            "metrics": parse(metrics, {}),
            "trading_style": style,
            "risk_flags": parse(risk, []),
            "cluster_id": cluster,
            "computed_at": computed_at,
        })
    doc = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "chain": "robinhood", "chain_id": 4663,
        "total_ranked": len(wallets),
        "source": "regenerated locally from wallet_scores (refresh_results_local.py)",
        "wallets": wallets,
    }
    (OUT / "top_wallets_latest.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    # CSV ringkas
    lines = ["rank,wallet,composite_score,style,realized_pnl_usd,win_rate,positions"]
    for w in wallets:
        m = w.get("metrics") or {}
        lines.append(",".join(str(x) for x in [
            w["rank"], w["wallet_address"], w["composite_score"],
            w.get("trading_style") or "",
            m.get("total_realized_pnl_usd", ""),
            m.get("win_rate", ""), m.get("total_positions", "")]))
    (OUT / "top_wallets_latest.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"total_ranked": len(wallets)}


if __name__ == "__main__":
    s1 = refresh_wallet_labels()
    print("wallet_labels.json:", s1["wallets_classified"], "wallets,",
          s1["label_rows"], "rows")
    print("  primary:", dict(list(s1["primary_types"].items())[:8]))
    s2 = refresh_top_wallets()
    print("top_wallets_latest:", s2)
    print("CATATAN: wallet_pool.json & whale_entry_maps.json tetap snapshot VPS "
          "(produk stage analyze — regenerasi via pipeline, bukan dump).")
