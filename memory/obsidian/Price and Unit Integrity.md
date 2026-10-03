---
title: "WalletIntel — Price and Unit Integrity"
status: current
tags: [project/WalletIntel, ai/risk]
---

# Price and Unit Integrity

Wallet valuation depends on token order, decimals, quote currency and price timestamp. The architecture describes swap-event price reconstruction; historical lessons show inverted orientation and near-zero quote points producing implausible valuations without obvious parser failure. A stored price series therefore still needs independent checks.

USD amounts, raw atoms, native quote amounts and pool ratios are different dimensions. A documented stable-quote assumption is not a universal live peg guarantee, and historical ETH/USD comparisons do not verify today's oracle. Attach coverage and freshness rather than filling missing prices with invented values.

The source chronology also records provider-envelope/list shape failures and stale mark problems. These can quietly create zero transfers or misleading returns. Preserve source/version evidence and flag incomplete observations so a composite score cannot conceal valuation uncertainty.

## Related topics

[[WalletIntel/Transaction Accounting]] · [[WalletIntel/PnL Verification]] · [[WalletIntel/Data Quality Lessons]] · [[TokenSniper/Data Integrity]]

## Provenance

[[WalletIntel/SOURCE_INDEX#^W03|W03]] · [[WalletIntel/SOURCE_INDEX#^W04|W04]] · [[WalletIntel/SOURCE_INDEX#^W06|W06]] · [[WalletIntel/SOURCE_INDEX#^W12|W12]]. Source ledger records hashes and read scope; documented behavior is not a freshly verified live service.
