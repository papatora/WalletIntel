---
title: "WalletIntel — Consumer Export Contract"
status: current
tags: [project/WalletIntel, ai/integration]
---

# Consumer Export Contract

WalletIntel's documented APIs/exports expose ranked metrics and verification evidence. Their existing payload shapes are not automatically the proposed TokenSniper envelope; an explicit versioned mapping is needed before interoperability can be claimed.

The consumer proposal carries chain/mint, producer, observation time, evidence IDs and confirmed action/confidence. Producer-owned history, tier calculations and verification details stay inside WalletIntel. TokenSniper consumes descriptive signals, does not import the database, and cannot turn transfer direction into a verified swap.

Freshness, unit conversion, error/unknown states and compatibility version must be stated at the boundary. A linked knowledge graph proves conceptual connection, not an active data feed. The producer's API examples remain examples rather than current measured wallet values.

## Related topics

[[WalletIntel/Producer Pipeline]] · [[WalletIntel/PnL Verification]] · [[WalletIntel/Scoring and Eligibility]] · [[Shared/DATA_CONTRACTS]] · [[TokenSniper/WalletIntel Contract]]

## Provenance

[[WalletIntel/SOURCE_INDEX#^W03|W03]] · [[WalletIntel/SOURCE_INDEX#^W04|W04]] · [[WalletIntel/SOURCE_INDEX#^W05|W05]] · [[WalletIntel/SOURCE_INDEX#^W10|W10]]. Source ledger records hashes and read scope; documented behavior is not a freshly verified live service.
