---
title: "WalletIntel — Data Quality Lessons"
status: historical
tags: [project/WalletIntel]
---

# WalletIntel — Data Quality Lessons

The documented landmines include wrong price orientation, wrong event topic shape, per-leg trade undercount, zero/noisy quote marks and database concurrency. Some errors produced plausible but incorrect results rather than explicit exceptions, so import success cannot certify economic correctness.

The fixed-ledger chronology records an API envelope/list mismatch that silently yielded no transfers and snapshot/transaction contention that delayed fresh data. These are failure mechanisms worth retaining without reproducing process commands, raw log counts or current service claims.

Later corrections supersede isolated earlier success statements. A fresh source hash identifies which record supports a lesson; it does not prove every historical performance figure in the document. Exports must preserve incomplete coverage, stale prices and verification status so consumers cannot mistake repaired infrastructure for validated alpha.

## Navigation

[[WalletIntel/WalletIntel|WalletIntel]] · [[WalletIntel/Price and Unit Integrity]] · [[WalletIntel/Transaction Accounting]]
