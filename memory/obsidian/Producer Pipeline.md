---
title: "WalletIntel — Producer Pipeline"
status: current
tags: [project/WalletIntel]
---

# WalletIntel — Producer Pipeline

WalletIntel produces wallet intelligence through discovery, historical price construction, enrichment, accounting, scoring and export. Its documented design persists observations and enrichment status so interrupted work can resume without treating repeated discovery as new evidence. The cluster describes that design; it does not verify a running pipeline or current record count.

Price construction and trade enrichment are separate steps. Wallet activity must be attached to an appropriate pool-price history before meaningful valuation. Rankings then summarize the wallet's global record, rather than declaring any holder of a selected token smart. Token-specific discovery and global wallet eligibility are different outputs.

The producer's documentation includes monitoring/export services, but they are not launched by this vault. Current consumer mappings remain proposed. Preserve lifecycle and freshness metadata in exports instead of copying an internal database into TokenSniper.

## Navigation

[[WalletIntel/WalletIntel|WalletIntel]] · [[WalletIntel/Discovery and Volume Signals]] · [[WalletIntel/Transaction Accounting]]
