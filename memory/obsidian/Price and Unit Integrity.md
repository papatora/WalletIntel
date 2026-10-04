---
title: "WalletIntel — Price and Unit Integrity"
status: current
tags: [project/WalletIntel]
---

# WalletIntel — Price and Unit Integrity

Wallet valuation depends on token order, decimals, quote currency and price timestamp. The architecture describes swap-event price reconstruction; historical lessons show inverted orientation and near-zero quote points producing implausible valuations without obvious parser failure. A stored price series therefore still needs independent checks.

USD amounts, raw atoms, native quote amounts and pool ratios are different dimensions. A documented stable-quote assumption is not a universal live peg guarantee, and historical ETH/USD comparisons do not verify today's oracle. Attach coverage and freshness rather than filling missing prices with invented values.

The source chronology also records provider-envelope/list shape failures and stale mark problems. These can quietly create zero transfers or misleading returns. Preserve source/version evidence and flag incomplete observations so a composite score cannot conceal valuation uncertainty.

## Navigation

[[WalletIntel/WalletIntel|WalletIntel]] · [[WalletIntel/Transaction Accounting]] · [[WalletIntel/PnL Verification]]
