# HANDOFF — PROMPT UNTUK SESI BARU (2026-10-06)

> Salin seluruh isi file ini ke sesi ZCode baru yang dibuka di folder repo
> `C:\Users\ROG\Documents\ClaudeCode\AlphaIntel\WalletIntel`. Semua konteks
> ada di file memory yang disebut di bawah — sesi baru WAJIB membacanya dulu.

---

## PROMPT UNTUK AGENT SESI BARU (salin mulai baris ini)

Kamu lanjutan sesi WalletIntel yang terputus. WAJIB baca dulu sebelum eksekusi
apa pun (urutan ini, jangan skip):

1. `PRE_COMPACT.md` — baca snapshot **S-50, S-51, S-51b..S-51i** (paling baru,
   paling penting). Snapshot lama S-1..S-49 hanya kalau butuh sejarah.
2. `SECURITY_POLICY.md` — aturan keras: kerja berat/scraping = VPS only;
   jangan install tool baru tanpa lapor; jangan sentuh dompet/kredensial.
3. `docs/FIXED_LEDGER.md` — semua bug yang pernah diperbaiki; JANGAN kerjakan
   ulang, JANGAN regresikan.
4. `C:\Users\ROG\Documents\Obsidian\AlphaIntel\WalletIntel\OPERATIONS_STATUS.md`
   dan `Smart Wallet Playbook.md` (Obsidian vault) — status operasional & playbook
   yang sedang diuji.
5. Konvensi laporan: tiap klaim pakai tag **[VPS]** (pipeline/scraping di 78.31.250.202)
   atau **[PC]** (explorer 8787, DB lokal, panen browser). Jangan halu: semua angka
   wajib ada bukti query/command, klaim "berfungsi" wajib ada bukti live.

## KONDISI TERAKHIR (terverifikasi 2026-10-06)

- Repo: `papatora/WalletIntel`, remote origin embed token (push tanpa klik).
- DB lokal: 170K wallet · 1,21 jt swap · live per 8 Okt. Delta harian:
  `python scripts/night_delta.py` (otomatis restore label lokal + wallet_social
  lewat `post_delta_reapply.py` — WAJIB setiap delta).
- Label final: INSIDER 8.268 · ACTIVE_MIN 32.842 (= "sudah dicek 9 detektor,
  tidak ada yang cocok" — BUKAN "belum diverifikasi") · GENERALIST 22.812 murni ·
  POOL_CONTRACT 120 (kontrak asli; 589 label EIP-7702 palsu sudah dihapus) ·
  NOISE 42 · CT 332 primary/397 label · DORMANT 1.591 · SNIPER 1.447 · MEV 487.
- Extension AutoLogin (`tools/autologin-extension/`): auto-heal login tiap 45 detik
  saat logged_out; Arkham/GMGN/Cielo terbukti ok. Jangan dibongkar.
- Explorer 8787 bind-first + build background; `/api/status` untuk health.
- `classify_local.py` = klasifikasi penuh di PC (compute-only) — jalankan
  setelah delta agar GENERALIST/ACTIVE_MIN tidak menumpuk; lalu
  `dedupe_generalist.py` (buang GENERALIST dgn label lain + invarian bucket)
  dan `refresh_results_local.py` + rebuild explorer.

## TUGAS TERTUNDA YANG WAJIB DILANJUTKAN (dari sesi sebelumnya)

1. **Smart Wallet Playbook — tahap net-flow derived** (mandat user): hitung
   net-flow wallet SMART dari **derived pricing** (price_points nearest-block
   per swap), BUKAN dari `usd_value` yang kini 100% NULL di dump VPS.
   Engine ada di `scripts/playbook_smart_confluence.py`; 598 wallet early≥2
   pump sudah teridentifikasi di `results/playbook/`.
2. **GMGN CopyTrade depth**: cursor pagination dicabut GMGN (sisi mereka).
   `scripts/gmgn_deep_harvest.py` siap rerun bila cursor kembali; saat ini
   depth = 100/tag. Jangan paksakan.
3. **Verifier R1–R3 utk 38 kandidat diamond** (`results/cielo/diamond_candidates_revised.json`)
   — jalur resmi: pipeline analyze [VPS].
4. **Audit S-51f findings**: semua P0/P1 sudah diperbaiki & terverifikasi.
   P2 tersisa ada di results/audit/audit_AJ_summary.json — prioritas rendah.

## YANG WAJIB DILAKUKAN TIAP SESI (daily, tanpa skip)

1. Delta harian (`night_delta.py`) → `classify_local.py` → `dedupe_generalist.py`
   → `refresh_results_local.py` → rebuild explorer → commit+push.
2. Verify GMGN trending + Arkham login state (extension auto-heal) + DB angka.
3. Update PRE_COMPACT (snapshot baru) + Obsidian OPERATIONS_STATUS + push.

## YANG DILARANG / JEBAKAN (sudah pernah terjadi — jangan ulangi)

- JANGAN bunuh proses python secara blind (cek commandline dulu — proses bisa
  delta harian/monitor/server).
- Background task WAJIB single-flight (relaunch tanpa kill = proses dobel
  berebut browser — insiden S-51f).
- Harvester browser: STICKY TAB per domain (arkm.com tab untuk arkham, gmgn.ai
  tab untuk gmgn) — `ctx.pages[0]` membajak tab lain.
- Content script MV3 = isolated world; CDP↔extension komunikasi via DOM dataset
  (`wiCmd`/`wiLogin`), bukan window function.
- Etherscan `address_transactions` default sort **asc** = tx TERLAMA — untuk
  "aktivitas terkini" wajib `sort='desc'` (salah = 52 label NOISE palsu, insiden S-51e).
- Guard 7702: panjang kode 7702 = 48 KARAKTER hex ('0x'+46), bukan 46.
- `usd_value` dump VPS baru = NULL semua; net flow wajib dihitung dari
  price_points derived (dataset.py sudah melakukannya; jangan baca usd_value).
- Jangan klaim "live-verified" tanpa bukti CDP/command tersimpan (insiden S-51b).
- GENERALIST hanya untuk wallet tanpa label lain (dedupe_generalist.py).
- GMGN rank depth = 100/tag (cursor dicabut sisi mereka) — jangan paksa.

## GAYA KERJA USER (wajib)

- Bahasa santai Indonesia boleh; jujur jangan manis — angka dari query, bukan
  perkiraan. Klaim tanpa bukti = halu = ditolak user.
- Kerjakan sampai tuntas tanpa bertanya hal kecil; laporkan progres berkala.
- Tiap milestone: PRE_COMPACT snapshot + commit + push + Obsidian.
- Tag lokasi [VPS]/[PC] di tiap klaim status.
