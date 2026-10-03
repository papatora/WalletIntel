---
title: "WalletIntel — Knowledge index"
status: current
tags: [project/WalletIntel, ai/core]
---

# Knowledge index

WalletIntel is an evidence producer within [[Shared/SYSTEM_ARCHITECTURE|AlphaIntel]]. Start at [[WalletIntel/CURRENT_STATE]]; the following topics extract documented methods without copying runtime/data or launching services.

- [[WalletIntel/Producer Pipeline]] — WalletIntel produces wallet intelligence through discovery, historical price construction, enrichment, accounting, scoring and export.
- [[WalletIntel/Wallet Identity]] — Identity is a chain-specific wallet address, not an account label, display name or a truncated screenshot.
- [[WalletIntel/Transaction Accounting]] — Documented accounting builds positions from classified buys and sells, realizes the proportional cost basis of sold slices, and values remaining holdings separately as unrealized.
- [[WalletIntel/Price and Unit Integrity]] — Wallet valuation depends on token order, decimals, quote currency and price timestamp.
- [[WalletIntel/PnL Verification]] — The documented hard verification model separates an independent quote/oracle cross-check, fresh raw trade re-derivation, and a stale-open rule.
- [[WalletIntel/Scoring and Eligibility]] — The documented composite combines win rate, median/max returns, timing percentiles, breadth/consistency and recency.
- [[WalletIntel/Anti Gaming and Clusters]] — Documented filters exclude insufficient data and receive-only airdrop records from ranked trader claims, while other patterns flag wash, insider, MEV, dust or clustering risk.
- [[WalletIntel/Discovery and Volume Signals]] — The volume-sweep directive harvests wallets associated with significant token activity.
- [[WalletIntel/Data Quality Lessons]] — The documented landmines include wrong price orientation, wrong event topic shape, per-leg trade undercount, zero/noisy quote marks and database concurrency.
- [[WalletIntel/Security and Operational Boundaries]] — Canonical policy separates local code/memory/offline tests from approved heavy pipeline and remote work.
- [[WalletIntel/Consumer Export Contract]] — WalletIntel's documented APIs/exports expose ranked metrics and verification evidence.

[[WalletIntel/Historical Knowledge]] keeps old lessons separate. [[WalletIntel/SOURCE_INDEX]] and SOURCE_LEDGER.json record source accounting and exclusions. [[Shared/DATA_CONTRACTS]] connects this producer to the [[TokenSniper/INDEX|offline paper consumer]]; [[INDEX|master index]] and [[GRAPH_LEGEND]] provide system navigation.
