---
title: "WalletIntel — PnL Verification"
status: current
tags: [project/WalletIntel, ai/risk]
---

# PnL Verification

The documented hard verification model separates an independent quote/oracle cross-check, fresh raw trade re-derivation, and a stale-open rule. Ranked results should preserve which checks passed and which observations were matched; a database-derived score alone is not verification.

The scoring document describes R1 quote consistency, R2 independent re-derivation of selected closed trades and R3 freshness of unrealized marks. Its stated tolerances and sampling are policy from that artifact, not a fresh proof of every trade or present deployment. Do not quote old reference prices as current.

The security policy forbids reporting new PnL without raw-data re-derivation and weakening verification to improve a leaderboard. Small or selectively checked samples remain limitations. Producers should export explicit status/provenance so consumers can reject unverified records rather than infer success from a tier name.

## Related topics

[[WalletIntel/Transaction Accounting]] · [[WalletIntel/Price and Unit Integrity]] · [[WalletIntel/Scoring and Eligibility]] · [[WalletIntel/Consumer Export Contract]] · [[TokenSniper/Anti-Hallucination Rules]]

## Provenance

[[WalletIntel/SOURCE_INDEX#^W02|W02]] · [[WalletIntel/SOURCE_INDEX#^W04|W04]] · [[WalletIntel/SOURCE_INDEX#^W07|W07]]. Source ledger records hashes and read scope; documented behavior is not a freshly verified live service.
