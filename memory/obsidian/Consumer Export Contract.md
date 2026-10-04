---
title: "WalletIntel — Consumer Export Contract"
status: current
tags: [project/WalletIntel]
---

# WalletIntel — Consumer Export Contract

WalletIntel's documented APIs/exports expose ranked metrics and verification evidence. Their existing payload shapes are not automatically the proposed TokenSniper envelope; an explicit versioned mapping is needed before interoperability can be claimed.

The consumer proposal carries chain/mint, producer, observation time, evidence IDs and confirmed action/confidence. Producer-owned history, tier calculations and verification details stay inside WalletIntel. TokenSniper consumes descriptive signals, does not import the database, and cannot turn transfer direction into a verified swap.

Freshness, unit conversion, error/unknown states and compatibility version must be stated at the boundary. A linked knowledge graph proves conceptual connection, not an active data feed. The producer's API examples remain examples rather than current measured wallet values.

## Navigation

[[WalletIntel/WalletIntel|WalletIntel]] · [[WalletIntel/Producer Pipeline]] · [[WalletIntel/PnL Verification]]

Shared boundary: [[Shared/WalletIntel Contract]].
