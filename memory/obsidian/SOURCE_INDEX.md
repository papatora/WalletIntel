---
title: "WalletIntel — Source provenance"
status: historical
tags: [project/WalletIntel, ai/history]
---

# Source provenance

This catalog is provenance, not an operational cluster. [[WalletIntel/INDEX]] routes current knowledge and [[WalletIntel/Historical Knowledge]] explains historical inputs. SOURCE_LEDGER.json records 12 canonical documentation sources and 24 historical source references, with full SHA256 and dispositions.

## W01 — README.md

**Scope:** Producer role, pipeline, local/VPS boundary and honest-limit sections. **Disposition:** documented-methodology. Durable documented methodology extracted; implementation and live state not revalidated by this curation

Routes: [[WalletIntel/Producer Pipeline]] · [[WalletIntel/Scoring and Eligibility]] · [[WalletIntel/Security and Operational Boundaries]]. Original SHA256: `cb4678f4df2f50bde7dc9d618d59fc89dd3e163252d92a0d11a3edb12613b9c2`. Full path is retained in SOURCE_LEDGER.json. ^W01

## W02 — SECURITY_POLICY.md

**Scope:** Complete sanitized policy; no credentials or remote commands copied. **Disposition:** documented-methodology. Durable documented methodology extracted; implementation and live state not revalidated by this curation

Routes: [[WalletIntel/PnL Verification]] · [[WalletIntel/Security and Operational Boundaries]]. Original SHA256: `87b9c8e69947f8f9eee7834a154b75baf84d6ba37b97a5a7b6b843625733d5d7`. Full path is retained in SOURCE_LEDGER.json. ^W02

## W03 — docs/ARCHITECTURE.md

**Scope:** Complete documented pipeline and resumption/scaling design. **Disposition:** documented-methodology. Durable documented methodology extracted; implementation and live state not revalidated by this curation

Routes: [[WalletIntel/Producer Pipeline]] · [[WalletIntel/Wallet Identity]] · [[WalletIntel/Transaction Accounting]] · [[WalletIntel/Price and Unit Integrity]] · [[WalletIntel/Discovery and Volume Signals]] · [[WalletIntel/Consumer Export Contract]]. Original SHA256: `d394e41d8e6e164030bed913f0fd00910458c362684e2caad67b3b8fd0643e33`. Full path is retained in SOURCE_LEDGER.json. ^W03

## W04 — docs/SCORING.md

**Scope:** Complete metric definitions, anti-gaming and R1/R2/R3 verification policy. **Disposition:** documented-methodology. Durable documented methodology extracted; implementation and live state not revalidated by this curation

Routes: [[WalletIntel/Transaction Accounting]] · [[WalletIntel/Price and Unit Integrity]] · [[WalletIntel/PnL Verification]] · [[WalletIntel/Scoring and Eligibility]] · [[WalletIntel/Anti Gaming and Clusters]] · [[WalletIntel/Consumer Export Contract]]. Original SHA256: `c847fff6627929f2f5697a06c18a89ef4f36fa6e31a25c2aa23a2b3d7ad7e783`. Full path is retained in SOURCE_LEDGER.json. ^W04

## W05 — docs/WALLET_TAXONOMY.md

**Scope:** Evidence/confidence rules and current taxonomy definitions; identity examples excluded. **Disposition:** documented-methodology. Durable documented methodology extracted; implementation and live state not revalidated by this curation

Routes: [[WalletIntel/Wallet Identity]] · [[WalletIntel/Anti Gaming and Clusters]] · [[WalletIntel/Consumer Export Contract]]. Original SHA256: `952c485d8f657d0bbe3424c0d3471ec8015df8fc3430072596424475eef2985e`. Full path is retained in SOURCE_LEDGER.json. ^W05

## W06 — docs/memory/05_TECHNICAL_LANDMINES.md

**Scope:** Complete historical technical lesson sections. **Disposition:** historical-reference. Dated snapshot/proposal retained as evidence; no operational restart or current health claim

Routes: [[WalletIntel/Transaction Accounting]] · [[WalletIntel/Price and Unit Integrity]] · [[WalletIntel/Data Quality Lessons]]. Original SHA256: `44dc5ff5a89c225155d715dccb65313368bdf46b4fa42e80c525d50d12ee0156`. Full path is retained in SOURCE_LEDGER.json. ^W06

## W07 — docs/memory/07_COPYTRADE_CRITERIA.md

**Scope:** Tier/eligibility method and caveats; identity examples excluded. **Disposition:** historical-reference. Dated snapshot/proposal retained as evidence; no operational restart or current health claim

Routes: [[WalletIntel/PnL Verification]] · [[WalletIntel/Scoring and Eligibility]] · [[WalletIntel/Anti Gaming and Clusters]]. Original SHA256: `1402b33929a57e5862270b341eef43d787783345a78f8cd729321eab353472a6`. Full path is retained in SOURCE_LEDGER.json. ^W07

## W08 — docs/DIRECTIVE_VOLUME_SWEEP.md

**Scope:** Complete dated discovery directive, not a running-state assertion. **Disposition:** historical-reference. Dated snapshot/proposal retained as evidence; no operational restart or current health claim

Routes: [[WalletIntel/Discovery and Volume Signals]]. Original SHA256: `96d91238824563820d38c537c47a31bd76bab0bbbe1f512fb5e9bec6eea35298`. Full path is retained in SOURCE_LEDGER.json. ^W08

## W09 — docs/memory/01_STATE.md

**Scope:** Complete dated state snapshot; counts/sessions excluded. **Disposition:** historical-reference. Dated snapshot/proposal retained as evidence; no operational restart or current health claim

Routes: [[WalletIntel/Data Quality Lessons]] · [[WalletIntel/Security and Operational Boundaries]]. Original SHA256: `c56f5f0888f6a99843c625c0c2bd23a73e8e7a9424048889c1dceb30c28bd8a9`. Full path is retained in SOURCE_LEDGER.json. ^W09

## W10 — docs/API.md

**Scope:** Complete documented export/API payload shape; example metrics excluded. **Disposition:** documented-methodology. Durable documented methodology extracted; implementation and live state not revalidated by this curation

Routes: [[WalletIntel/Consumer Export Contract]]. Original SHA256: `84d328adc21926d55905abafd5527e8f8271d657d03a8e720f4e0452ef7bd3f3`. Full path is retained in SOURCE_LEDGER.json. ^W10

## W11 — MIGRATION_REPORT.md

**Scope:** Canonical relocation and remote/publishing disposition sections. **Disposition:** documented-methodology. Durable documented methodology extracted; implementation and live state not revalidated by this curation

Routes: [[WalletIntel/Security and Operational Boundaries]]. Original SHA256: `7b5edfce88dcb870bf6b7bad37f1406805dfdc6aea08be605695dc9ba73d308f`. Full path is retained in SOURCE_LEDGER.json. ^W11

## W12 — docs/FIXED_LEDGER.md

**Scope:** Pipeline/data lesson sections and latest S47 tail; chronological intermediate examples excluded. **Disposition:** historical-reference. Dated snapshot/proposal retained as evidence; no operational restart or current health claim

Routes: [[WalletIntel/Price and Unit Integrity]] · [[WalletIntel/Discovery and Volume Signals]] · [[WalletIntel/Data Quality Lessons]] · [[WalletIntel/Security and Operational Boundaries]]. Original SHA256: `2bffc6c9abb817c6bd8c819e3ad00971dd559a6004bccfe26236b81245cba54a`. Full path is retained in SOURCE_LEDGER.json. ^W12

## Historical input coverage

- [[TokenSniper/ARCHIVE_INDEX#^S34|S34]] → [[WalletIntel/Historical Knowledge]].
- [[TokenSniper/ARCHIVE_INDEX#^S35|S35]] → [[WalletIntel/Historical Knowledge]].
- [[TokenSniper/ARCHIVE_INDEX#^S36|S36]] → [[WalletIntel/Historical Knowledge]].
- [[TokenSniper/ARCHIVE_INDEX#^S37|S37]] → [[WalletIntel/Historical Knowledge]].
- [[TokenSniper/ARCHIVE_INDEX#^S38|S38]] → [[WalletIntel/Historical Knowledge]].
- [[TokenSniper/ARCHIVE_INDEX#^S39|S39]] → [[WalletIntel/Historical Knowledge]].
- [[TokenSniper/ARCHIVE_INDEX#^S40|S40]] → [[WalletIntel/Historical Knowledge]].
- [[TokenSniper/ARCHIVE_INDEX#^S41|S41]] → [[WalletIntel/Historical Knowledge]].
- [[TokenSniper/ARCHIVE_INDEX#^S42|S42]] → [[WalletIntel/Historical Knowledge]].
- [[TokenSniper/ARCHIVE_INDEX#^S43|S43]] → [[WalletIntel/Historical Knowledge]].
- [[TokenSniper/ARCHIVE_INDEX#^S44|S44]] → [[WalletIntel/Historical Knowledge]].
- [[TokenSniper/ARCHIVE_INDEX#^S45|S45]] → [[WalletIntel/Historical Knowledge]].
- [[TokenSniper/ARCHIVE_INDEX#^S46|S46]] → [[WalletIntel/Historical Knowledge]].
- [[TokenSniper/ARCHIVE_INDEX#^S47|S47]] → [[WalletIntel/Historical Knowledge]].
- [[TokenSniper/ARCHIVE_INDEX#^S48|S48]] → [[WalletIntel/Historical Knowledge]].
- [[TokenSniper/ARCHIVE_INDEX#^S49|S49]] → [[WalletIntel/Historical Knowledge]].
- [[TokenSniper/ARCHIVE_INDEX#^S50|S50]] → [[WalletIntel/Historical Knowledge]].
- [[TokenSniper/ARCHIVE_INDEX#^S51|S51]] → [[WalletIntel/Historical Knowledge]].
- [[TokenSniper/ARCHIVE_INDEX#^S52|S52]] → [[WalletIntel/Historical Knowledge]].
- [[TokenSniper/ARCHIVE_INDEX#^S53|S53]] → [[WalletIntel/Historical Knowledge]].
- [[TokenSniper/ARCHIVE_INDEX#^S54|S54]] → [[WalletIntel/Historical Knowledge]].
- [[TokenSniper/ARCHIVE_INDEX#^S55|S55]] → [[WalletIntel/Historical Knowledge]].
- [[TokenSniper/ARCHIVE_INDEX#^S56|S56]] → [[WalletIntel/Historical Knowledge]].
- [[TokenSniper/ARCHIVE_INDEX#^S57|S57]] → [[WalletIntel/Historical Knowledge]].
