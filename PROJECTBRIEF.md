# PROJECT BRIEF — Faultline

> Pipeline data gempa Indonesia: data diambil otomatis setiap hari, dibersihkan, disimpan dalam model gudang data (star schema), lalu dianalisis di dashboard.

Rancangan teknis: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · Urutan kerja: [`docs/ROADMAP.md`](docs/ROADMAP.md) · Tampilan: [`docs/DESIGN.md`](docs/DESIGN.md)

---

## 1. Ringkasan

| | |
|---|---|
| **Nama** | Faultline — Analitik Gempa Indonesia |
| **Jenis** | Proyek rekayasa data: ETL + data warehouse + dashboard |
| **Pemilik** | Naufal Dzaky — Teknologi Informasi UGM |
| **Tujuan utama** | Portofolio rekayasa dan analitik data (ETL, data warehouse, BI) |
| **Target waktu MVP** | 1 hari kerja |
| **Sumber data** | USGS Earthquake Catalog (FDSN Event API), publik, tanpa API key |

### Kenapa proyek ini ada

Faultline menunjukkan alur rekayasa data dari ujung ke ujung: pipeline yang berjalan sendiri setiap hari, idempoten, punya pemeriksaan kualitas data, dan disimpan dalam model gudang data yang benar.

> **Catatan kejujuran.** Data berasal dari katalog USGS, bukan BMKG. Faultline adalah proyek analitik, **bukan sumber informasi darurat atau peringatan dini**. Hal ini ditulis di dashboard dan README.

---

## 2. Masalah

- Data gempa tersedia publik, tapi mentah: format JSON bertingkat, waktu dalam milidetik UTC, tidak ada pengelompokan wilayah, dan catatan bisa **direvisi** beberapa hari setelah kejadian (magnitudo diperbarui, status `automatic` → `reviewed`).
- Untuk menjawab pertanyaan sederhana — *"wilayah mana yang paling sering gempa kuat dalam 10 tahun terakhir?"* — orang harus mengunduh, membersihkan, dan mengolah sendiri.

## 3. Solusi

1. **Extract** — mengambil data dari USGS per jendela waktu (bulanan untuk backfill, 30 hari terakhir untuk harian).
2. **Transform** — meratakan JSON, mengonversi waktu, menetapkan wilayah, kelas kedalaman, dan kelas magnitudo; menolak baris yang tidak valid dengan alasan tercatat.
3. **Load** — upsert ke tabel fakta sehingga revisi USGS memperbarui baris lama tanpa duplikasi; data mentah disimpan di staging.
4. **Jadwal** — GitHub Actions menjalankan ETL setiap hari.
5. **Analitik** — view SQL + dashboard Streamlit dengan filter.

---

## 4. Pengguna

| Persona | Kebutuhan |
|---|---|
| **Analis / recruiter yang menilai portofolio** | Melihat pipeline yang rapi, bisa dijalankan ulang, dan hasilnya masuk akal |
| **Pembaca umum** (mahasiswa, jurnalis data) | Melihat pola gempa Indonesia per wilayah, waktu, kedalaman, dan magnitudo |

---

## 5. Ruang lingkup

### Masuk MVP

- Backfill 2016-01-01 sampai hari ini, magnitudo ≥ 4.0, wilayah Indonesia (kotak batas di ARCHITECTURE).
- Run harian inkremental (30 hari terakhir) lewat GitHub Actions.
- Star schema: `fakta_gempa`, `dim_tanggal`, `dim_wilayah`; staging mentah; log ETL; tabel baris ditolak.
- 6 view analitik.
- Dashboard Streamlit: filter, 4 kartu angka, 5 visual, tabel 10 gempa terkuat.
- Test pytest untuk transform dan aturan kualitas.
- README dengan diagram alur data.

### Tidak masuk MVP

- Data BMKG, integrasi peta batas provinsi resmi.
- Prediksi gempa (tidak ilmiah untuk proyek ini — dan tidak etis untuk diklaim).
- Notifikasi real-time.

---

## 6. User stories & kriteria terima

### US-1 — Backfill yang bisa diulang
- [ ] `python -m etl.run --mode backfill --mulai 2016-01-01` mengisi gudang data.
- [ ] Menjalankan perintah yang sama dua kali **tidak menambah baris** (idempoten).
- [ ] Setiap run tercatat di `etl_log` dengan jumlah diambil, insert, update, dan ditolak.

### US-2 — Revisi data tertangani
- [ ] Jika USGS memperbarui magnitudo suatu gempa, run berikutnya memperbarui baris di `fakta_gempa` (dibandingkan lewat kolom `diperbarui_pada`).
- [ ] Baris lama tidak pernah tertimpa data yang lebih tua.

### US-3 — Kualitas data
- [ ] Baris tanpa magnitudo/koordinat, kedalaman di luar −5…800 km, atau `type` selain `earthquake` ditolak dan dicatat di `etl_ditolak` dengan alasannya.
- [ ] Dashboard menampilkan "x baris ditolak pada run terakhir".

### US-4 — Run otomatis harian
- [ ] Workflow GitHub Actions berjalan terjadwal dan bisa dipicu manual.
- [ ] Rahasia (`DATABASE_URL`) tersimpan di GitHub Secrets.

### US-5 — Dashboard analitik
- [ ] Filter: rentang tanggal, magnitudo minimum, wilayah.
- [ ] Kartu angka: total gempa, gempa M ≥ 6, rata-rata kedalaman, waktu run ETL terakhir.
- [ ] Visual: tren bulanan, peta titik, distribusi magnitudo, komposisi kedalaman, perbandingan wilayah.
- [ ] Tabel 10 gempa terkuat dengan waktu WIB.
- [ ] Semua angka berasal dari view SQL.

---

## 7. Metrik keberhasilan

| Metrik | Target |
|---|---|
| Backfill 10 tahun selesai | < 10 menit |
| Run harian otomatis berhasil | 3 hari berturut-turut setelah rilis |
| Test pytest | ≥ 10 kasus, semua hijau |
| Dashboard publik | Bisa dibuka tanpa login |

## 8. Risiko

| Risiko | Mitigasi |
|---|---|
| API USGS lambat atau menolak permintaan | Jeda 1 detik antar-request, retry dengan backoff, User-Agent jelas |
| Batas wilayah kasar membuat gempa salah wilayah | Ditulis terang sebagai pendekatan; kolom `tempat` asli tetap disimpan |
| Katalog USGS kurang lengkap untuk gempa kecil di Indonesia | Batas magnitudo ≥ 4.0, disebut di README |
| Waktu tidak cukup | *Cut list* di ROADMAP |
