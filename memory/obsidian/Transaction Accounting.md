---
title: "WalletIntel — Transaction Accounting"
status: current
tags: [project/WalletIntel]
---

# WalletIntel — Transaction Accounting

Documented accounting builds positions from classified buys and sells, realizes the proportional cost basis of sold slices, and values remaining holdings separately as unrealized. Plain incoming/outgoing transfers must not silently become swaps. Return multiple depends on the sold slice's cost and proceeds under a stated method.

The technical lesson record warns that per-leg classification drops router-mediated trades. Grouping token flow at transaction level preserves wallet/pool relationships through intermediary legs. This is a source-supported correction, not permission to count any router interaction as a verified trade without underlying flow evidence.

Realized and unrealized totals answer different questions. A stale mark can inflate a remaining position while closed proceeds are verifiable. Keep both quantities, costs, coverage and uncertainty separate in exports; the offline consumer's hypothetical fills are a different model.

## Navigation

[[WalletIntel/WalletIntel|WalletIntel]] · [[WalletIntel/Price and Unit Integrity]] · [[WalletIntel/PnL Verification]]
