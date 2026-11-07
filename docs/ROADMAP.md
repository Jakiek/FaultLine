# ROADMAP — Faultline

## Ringkasan proyek

Pipeline ETL gempa Indonesia (USGS → PostgreSQL star schema) yang berjalan otomatis setiap hari, plus dashboard Streamlit. Target **±1 hari**. Detail kebutuhan di [`../PROJECTBRIEF.md`](../PROJECTBRIEF.md).

## Aturan main sepanjang proyek

1. **Satu fase sampai *definition of done*, baru lanjut.**
2. **Test transform ditulis bersamaan dengan kodenya**, bukan di akhir.
3. **Setiap fase ditutup dengan commit yang rapi** dan pesan commit yang jelas.
4. **Kalau tertinggal, pakai *cut list*.**

## Peta fase

| Fase | Isi | Waktu |
|---|---|---|
| 0 | Persiapan repo, venv, Neon | 30 mnt |
| 1 | Skema SQL + dim_tanggal + dim_wilayah | 1 jam |
| 2 | Extract + simpan staging | 1,5 jam |
| 3 | Transform + aturan kualitas + test | 2 jam |
| 4 | Load (upsert) + log + backfill penuh | 1,5 jam |
| 5 | View analitik + dashboard | 2,5 jam |
| 6 | GitHub Actions + deploy dashboard + README | 1,5 jam |

Total ±10,5 jam.

---

## Fase 0 — Persiapan (30 menit)

Status: venv, `requirements.txt` berversi tetap, `.env` diabaikan git, repo lokal. Neon dan repo GitHub publik belum dibuat; pengembangan memakai PostgreSQL lokal.

- Repo `faultline` (public), salin `PROJECTBRIEF.md`, `.gitignore`, `docs/`. **Pastikan `.gitignore` ada sebelum commit pertama.**
- `python -m venv .venv`, `requirements.txt`: `requests`, `psycopg[binary]`, `python-dotenv`, `pandas`, `streamlit`, `plotly`, `pytest`.
- Project Neon baru → `DATABASE_URL` di `.env` (masuk `.gitignore`).

**Done:** `python -c "import psycopg; print('ok')"` jalan, `.env` tidak ter-commit.

---

## Fase 1 — Skema (1 jam)

Status: selesai di PostgreSQL lokal (`dim_tanggal` 5.479 baris, `dim_wilayah` 8 baris). Runner migrasi mencatat file di `skema_migrasi` sehingga `init` aman diulang. Belum dijalankan di Neon.

- `sql/001_skema.sql`, `sql/002_dim_tanggal.sql` (generate 2016-01-01 s.d. 2030-12-31 dengan `generate_series`), isi `dim_wilayah` 8 baris.
- Skrip kecil `python -m etl.run --mode init` yang menjalankan file SQL berurutan.

**Done:** semua tabel ada di Neon; `SELECT COUNT(*) FROM dim_tanggal` ≈ 5.479.

**Jebakan:** `tanggal_id` dibuat dari tanggal WIB padahal waktu disimpan UTC. Tetapkan: `tanggal_id` dari **tanggal UTC**, dan tulis alasannya sebagai komentar di `sql/001_skema.sql`.

---

## Fase 2 — Extract (1,5 jam)

Status: selesai. Januari 2024 terambil (173 fitur); retry terbukti saat USGS memutus koneksi sekali. Fixture berisi 1 fitur asli dan 2 salinan yang disunting.

- `etl/extract.py`: `ambil_jendela(mulai, selesai)` dengan parameter tetap, retry, backoff, jeda 1 detik, User-Agent.
- Simpan fitur mentah ke `stg_gempa_mentah` dengan `run_id`.
- Simpan 3 fitur asli ke `tests/fixtures/usgs_contoh.json` (1 normal, 1 `quarry blast`, 1 tanpa magnitudo — kalau tidak ada, sunting salinannya).

**Done:** satu jendela bulan (mis. Januari 2024) terambil dan tersimpan di staging.

**Jebakan:** lupa `orderby=time-asc` → pagination tidak stabil; jendela terlalu besar → kena batas 20.000 fitur per request.

---

## Fase 3 — Transform & kualitas (2 jam)

Status: selesai. Semua 10 kasus wajib tercakup bersama kasus tambahan; `pytest` hijau.

- `etl/transform.py`, `etl/quality.py`, `etl/wilayah.py` sesuai ARCHITECTURE § 7.
- Test minimal 10 kasus:
  1. ms → `datetime` UTC benar.
  2. Koordinat GeoJSON `[bujur, lintang, kedalaman]` tidak tertukar.
  3–5. Kelas kedalaman di batas 69,9 / 70 / 300 / 300,1 km.
  6. Kelas magnitudo di batas 4,9 / 5,0.
  7. Titik di Jakarta → Jawa; titik di Selat Sunda (105,5; −6) → Jawa (urutan cek).
  8. Titik di laut Banda → Maluku / Lainnya sesuai tabel.
  9. `quarry blast` ditolak dengan kode `Q2`.
  10. Duplikat dalam batch → yang `updated` terbaru menang (`Q5`).

**Done:** `pytest` hijau.

**Jebakan:** urutan koordinat GeoJSON adalah **bujur dulu**, baru lintang.

---

## Fase 4 — Load & backfill (1,5 jam)

Status: selesai di PostgreSQL lokal; angka dua kali run tercatat di README bagian "Idempoten".

- `etl/load.py`: upsert sesuai ARCHITECTURE § 6.2, simpan penolakan, catat `etl_log`.
- `etl/run.py --mode backfill --mulai 2016-01-01`.
- Jalankan backfill **dua kali**.

**Done:**
- Run pertama: `jumlah_insert` > 0.
- Run kedua: `jumlah_insert = 0`, jumlah baris `fakta_gempa` tidak berubah (bukti idempoten).
- Catat kedua angka di README (bagian "Idempoten").

**Jebakan:** commit per jendela bulan, bukan sekali di akhir, supaya kegagalan di bulan ke-90 tidak membatalkan semuanya.

---

## Fase 5 — View & dashboard (2,5 jam)

Status: selesai lokal. Dashboard diuji headless dengan AppTest Streamlit (tanpa exception; state filter kosong dan reset berfungsi). Filter memakai view datar `v_gempa` (ADR 001). Pemeriksaan visual di browser dan screenshot belum.

- `sql/003_view.sql`.
- `dashboard/queries.py` (semua SQL di satu tempat, berparameter) dan `dashboard/app.py` sesuai DESIGN § 4.
- `@st.cache_data(ttl=600)` untuk query.

**Done:** US-5 lolos semua kriteria; semua waktu tampil dalam WIB.

**Jebakan:** menghitung agregat di pandas padahal sudah ada view-nya.

---

## Fase 6 — Otomatisasi & rilis (1,5 jam)

Status: workflow dan README siap. GitHub Secrets, run Actions pertama, Neon, dan deploy Streamlit menunggu otorisasi pemilik.

- `.github/workflows/etl-harian.yml` + `DATABASE_URL` di GitHub Secrets; jalankan sekali lewat *Run workflow*.
- Deploy dashboard ke Streamlit Community Cloud; `DATABASE_URL` di Secrets Streamlit.
- README: diagram alur data, cara menjalankan, keputusan desain, batasan data, screenshot.
- 3 screenshot untuk portofolio: dashboard penuh, peta, dan tampilan `etl_log` (bukti idempoten).

**Done:** workflow hijau di tab Actions; dashboard publik terbuka tanpa login.

---

## Cut list (kalau tertinggal)

1. Peta titik (ganti tabel per wilayah).
2. Filter wilayah di sidebar (sisakan rentang tanggal & magnitudo).
3. Backfill dari 2020, bukan 2016.

**Jangan dipotong:** idempoten + bukti dua kali run, aturan kualitas + `etl_ditolak`, test transform, GitHub Actions, README dengan diagram.
