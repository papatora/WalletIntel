# Pelajaran Riset: Arketipe Rug Pons + Disiplin Backtest (S-55)

> Sumber: materi dari teman user (`C:\Users\ROG\Documents\ClaudeCode\anotherresearchtoken`
> — research.txt + 9 gambar, Agustus 2026). Hasil riil terverifikasi profil
> GMGN: modal $16 (claim lending emissions) → $764,31 dalam dua siklus strategi.
> Ini CATATAN PEMBELAJARAN — bukan ajakan; strateginya sendiri sudah decay.

## 1. Arketipe rug "tangga" (staircase) di Pons

- ~70% launch Pons V1 saat itu polanya sama: harga naik tangga pelan
  (FCFS chain — tak ada yang bisa menyodok), lalu **rug instan**.
- Kontrak Pons V1 dari factory resmi = verified, **tidak bisa honeypot**
  (selalu bisa jual) — jadi pola ini bukan honeypot, murni timing dev.
- Chart GMGN menandai DB/DO/DS (dev buy/open/sell) — contoh ANON: tangga ke
  $38,7K lalu 1 candle merah ke $2,5K.

## 2. Fingerprint dev (yang paling actionable)

- **Dev umumnya beli 0,6–3 ETH saat launch**, lalu exit.
- **TP 4x**: p80 rug terjadi ~4x mcap awal → ikut beli saat dev beli 0,6-3 ETH,
  ambil profit di 4x apa pun yang terjadi.
- **Varian 3-3,5 ETH**: p80 rug ~90 detik → exit bersih di 90 detik,
  RR 1:0,3 tapi win-rate tinggi (salah = kehilangan posisi penuh).
- **Kejutan approve**: dev harus `approve` token sebelum jual → memantau
  approve event dev = sinyal exit PALING AWAL (bisa lebih cepat dari dev di
  chain FCFS). Mati saat dev mulai pre-approve di launch — edge decay.

## 3. Disiplin metodologi (pelajaran meta yang paling berharga)

1. **IS → OOS → FORWARD → Paper**: train split, eval split, forward day,
   lalu paper 12 jam. Deploy hanya kalau lolos permutasi + **buang top-10
   trade** dan tetap profit (uji kekokoran, bukan keberuntungan).
2. **Edge selalu decay** — dev beradaptasi (pre-approve, delay 30 detik).
   Strategi = perishable; terus riset play baru.
3. Data historis massal via **HyperSync** (envio.dev); real-time via
   **WSS logs** (Alchemy/official Robinhood RPC).
4. Sizing: entry kecil tetap ($1-10), `size = 0.0181 · √bankroll`.
5. Exit stack komposit berurutan (short-circuit OR):
   DevDumpExit → TP 4x → DumpOnsetExit (log-drop 1.2 dari peak 60s) →
   TrailingStop 50% → MaxHold 900s.

## 4. Pemetaan ke WalletIntel

| Pelajaran | Status di kita |
|---|---|
| dev-buy size → statistik rug | `scripts/pons_rug_archetype.py` (studi kohort IS/OOS di data kita — hasil di results/pons_archetype/study.json) |
| approve-dev sebagai sinyal paling awal | BELUM — butuh pemantauan Approval event (eth_getLogs topic 0x8c5be…) di VPS utk wallet dev; kandidat fitur live |
| roster/FRESH filter (skip bila operator terkenal muncul di 24 jam) | parsial — kita punya cluster/known_entities; bisa jadi filter playbook |
| IS/OOS/FORWARD/Paper utk strategi playbook | playbook saat ini compute-only; kerangka split IS/OOS sudah ada di studi kohort |
| HyperSync utk data massal | belum dipakai — kandidat kalau butuh histori penuh tanpa dump VPS |

## 5. Validasi angka di data kita

Lihat `results/pons_archetype/study.json` + stdout `scripts/pons_rug_archetype.py`
— kohort dev-buy 0,6-3 ETH vs 3-3,5 ETH: median/p80 waktu-rug, kelipatan
harga maksimum p50/p80, % yang pernah menyentuh 4x, split IS/OOS. Angka
temanmu berasal dari data Agustus; studi kita mengukur ulang di snapshot Okt.

## 6. Hasil validasi di data kita (20 Okt 2026 — results/pons_archetype/study.json)

1.515 token (≥12 swap) · IS 1.060 · OOS 455 (launch ≥ 30 Sep):

| Kohort | n | dev_eth median | rug p50 | maxx p50 | reach 4x |
|---|---|---|---|---|---|
| 0,6-3,0 ETH (ALL) | 96 | 1,18 | 3,4 jam | **6,9x** | **72,9%** |
| 0,6-3,0 ETH (OOS) | 46 | 1,44 | 1,9 jam | **15,1x** | **84,8%** |
| 3,0-3,5 ETH (ALL) | 12 | 3,17 | 91 menit | 10,4x | 66,7% |
| di luar kohort | 1.407 | **0,046** | 1,7 jam | 4,4x | 52,3% |

**Kesimpulan jujur:**
- ✅ Fingerprint "dev beli 0,6-3 ETH" TERKONFIRMASI ada kohornya (median 1,18 ETH)
  dan TP 4x realistis: 73% (semua) → 85% (OOS) launch kohort ini pernah menyentuh 4x.
- ✅ Launch DI LUAR kohort (dev beli receh ~0,05 ETH) jauh lebih lemah: maxx
  p50 cuma 4,4x — ukuran beli dev memang memisahkan kualitas launch.
- ⚠️ "p80 rug 90 detik utk 3-3,5 ETH" TIDAK mereplikasi di data kita (p50 ±91
  menit) — tapi n=12/n=5 saja, dan metrik rug kita (-80% dr peak di
  price_points) lebih kasar dari tick-level mereka. Jangan disimpulkan mati.
- ⚠️ p80 waktu-rug kita tergelembung sensor (token belum-rug dihitung sampai
  akhir data) — p50 yang lebih bermakna.
- Insight OOS: maxx p50 naik 6,9x → 15x utk kohort 0,6-3 ETH di launch baru —
  arah sebaliknya dari decay temanmu; pantau, jangan anggap permanen.

## 7. Follow-up (belum dikerjakan — antrean)
- Pemantauan Approval event dev (sinyal exit paling awal) — butuh watcher WSS
  di VPS; strategi live BUKAN mandat riset kita (kita intel), tapi DETEKSInya
  memperkaya label (mis. DEV_PREAPPROVED).
- Kalibrasi ulang konstanta waktu pakai tick-level (butuh data wss/log mentah).
