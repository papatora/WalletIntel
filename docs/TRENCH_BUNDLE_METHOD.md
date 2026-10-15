# Trench.bot Bundle Detection — Review & Reverse-Engineering (S-54)

> Sumber: dokumentasi resmi GitBook mereka (publik, versi markdown resmi via
> `docs.trench.bot/<page>.md` — tersimpan di `results/trench_docs/`) + aturan
> ringkas dari user (Telegram, Okt 2026). Semua klaim di bawah = dari dokumen
> MEREKA, bukan tebakan kita.

## Apa yang mereka deteksi

**Bundle** = beberapa wallet yang dikendalikan satu pihak membeli supply token
saat launch, supaya sniper/whale asli tidak kebagian — dan supaya terlihat ramai.
Evolusi metodenya (versi mereka):

1. **Era 1 — same-tx bundle**: banyak buy dalam SATU transaksi (dulu, mudah
   kedeteksi).
2. **Era 2 — mass snipe terkoordinasi**: buy dalam transaksi TERPISAH tapi
   **slot sama** (Solana slot ≈ 0,4 dtk). Di EVM (kita): **block sama**.
3. **Evasi bubblemap**: funder (CEX/mixer) mendanai semua wallet bundle SEBELUM
   launch; funder tidak pernah nyentuh coin → bubblemap tidak menghubungkan
   mereka. **Ini persis lapisan funding yang kita punya** (INDUKAN/first-funder,
   cluster by funder) dan mereka akui bubblemaps melewatkannya.

## Metode inti mereka (yang bisa kita porting)

### A. Bundle scanner (slot viewer)
- Kelompokkan BUY per slot/block di awal launch.
- **Bundle = ≥3 wallet unik dalam slot/block sama.** 2 wallet = zona
  false-positive (copy-trader, sniper cepat bisa kebetulan tabrakan).
- Per bundle laporkan: jumlah wallet unik, SOL keluar, **% supply dibeli** dan
  **% supply MASIH dipegang** (retensi; dibedakan dari total-bought karena dev
  bisa jual lalu beli lagi → >100% = wash).
- Red flag ekstrem (contoh mereka): 24 wallet satu slot pegang 76% supply.

### B. Bundle Risk Index (BRI) — skor risiko 0-100
4 faktor berbobot:
| Faktor | Bobot | Isi |
|---|---|---|
| Funding | 50% | wallet berbagi sumber dana (CEX/mixer/multi-hop), kedekatan waktu funding |
| Temporal | 40% | first-trade saling berdekatan (menit), sinkronisasi entry |
| Komposisi wallet | 25% | % wallet baru (dibuat dekat launch), % sniper, unknown |
| Behavioral | 20% | kemiripan jumlah buy, pola hold/sell terkoordinasi |

- Band: **70-100 VERY HIGH · 40-69 HIGH · 20-39 MEDIUM · 0-19 LOW**.
- Panduan: <20 aman-ish; 20-40 hati-hati; >40 risiko tinggi.
- Tipe cluster: Hybrid Strong (temporal+funding = tertinggi), Hybrid Weak,
  Temporal Only, Funding Only.
- Red flag tambahan: wallet baru >60%, top-20 holder >80% supply, wash
  (beli >100% supply / retensi <20% / volume besar tanpa dampak harga).

### C. Rules cepat versi user (60-detik check)
1. trench.bot: cluster risiko 70%+ = skip; cluster pegang 10%+ supply = skip.
2. jito explorer: 4 buy nempel persis di belakang dev tx = wallet mereka;
   pegang 20%+ = skip.
3. pump.fun trades: dev jual <1 menit = skip; top-10 holder >30% (ex pool) = skip.
4. **1 merah = skip. Semua hijau = tetap beli kecil.**

## Porting ke WalletIntel (Robinhood chain) — scripts/bundle_risk.py

| Konsep trench | Implementasi kita |
|---|---|
| slot (0,4 dtk) | `block_num` (RH ~0,1 dtk/block; 60 dtk ≈ 600 block) |
| block-0 bundle | BUY unik per block dalam creation..+2 block, ≥3 wallet |
| "4 buy nempel belakang dev" | block creation..+30, ≥4 wallet satu block |
| sumber dana bersama | funder dari `wallet_labels.evidence` (CLUSTER_MEMBER/RING_RECIPIENT/INSIDER senders) + known_entities — **lapisan funding kita sudah ada sejak S-43** |
| wallet baru | `wallets.first_seen` ≤2 hari dari `tokens.first_seen` |
| sniper/unknown | label SNIPER/BUNDLER_SUSPECT |
| % supply | `eth_call totalSupply` sekali per token (cache); gagal RPC = flag coverage |
| dev jual <1 menit | swap pertama dev (first BUY) vs SELL ≤60 dtk |
| top-10 holder >30% | net posisi wallet ter-track (ex pool) / supply |
| temporal rapat | sliding window 10 menit atas first-buy early set |
| behavioral | CV (koefisien variasi) jumlah buy pertama antar wallet cluster — CV rendah = bot |

**Verdict**: ada ≥1 red flag → SKIP (aturan user); else CAUTION kalau BRI ≥20
atau top-10 >20%; else PASS. Output: `results/bundle_risk/<ca>.json` +
`results/bundle_risk/scan.json` (batch semua pump token playbook).

**Integrasi**: halaman **Cek Token** (#/lookup) kini menjalankan analisis ini
per token — masuk sebagai komponen rating "Bundle Risk (trench-style)"
(penalti −1/flag, maks −3,5) + payload `bundle_risk` lengkap di JSON.

## Keterbatasan jujur (dicatat di output engine)

1. Coverage kita parsial: konsentrasi holder hanya wallet yang ter-track di DB
   (pembeli di luar snapshot tidak terhitung) — supply on-chain dari RPC bikin
   persentase tidak over-claim, tapi pembeli tak-tertrack bisa bikin
   under-estimate konsentrasi.
2. False positive (diakui docs mereka): withdraw CEX sama, bot populer,
   kebetulan timing saat ramai — makanya ambang ≥3 wallet + perlu supply besar.
3. Pump.fun-specific angka mereka (block 0, curve) tidak identik dengan RH
   chain — konstanta (2 block / 30 block / 60 dtk) = adaptasi wajar, bisa
   dikalibrasi dengan data kita belakangan.
