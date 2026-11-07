# CONVENTIONS — Faultline

Aturan teknis yang berlaku untuk semua kode di repo ini.

---

## Konteks

Faultline adalah pipeline ETL gempa Indonesia: data USGS diambil setiap hari, dibersihkan, dimuat ke gudang data PostgreSQL (star schema), lalu ditampilkan di dashboard Streamlit.

Kebutuhan: [`PROJECTBRIEF.md`](PROJECTBRIEF.md) · Rancangan: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · Urutan kerja: [`docs/ROADMAP.md`](docs/ROADMAP.md) · Tampilan: [`docs/DESIGN.md`](docs/DESIGN.md)

---

## Aturan domain — tidak boleh dilanggar

1. **ETL harus idempoten.** Menjalankan rentang yang sama dua kali tidak boleh menambah baris. Load selalu `INSERT ... ON CONFLICT (event_id) DO UPDATE ... WHERE fakta_gempa.diperbarui_pada < EXCLUDED.diperbarui_pada`.
2. **Waktu disimpan UTC.** Konversi ke WIB hanya di dashboard. `tanggal_id` diturunkan dari tanggal UTC.
3. **Koordinat GeoJSON adalah `[bujur, lintang, kedalaman]`.** Bukan lintang dulu.
4. **Staging mentah tidak dihapus oleh ETL.** Transform bisa diulang dari staging.
5. **Baris tidak valid ditolak dengan alasan**, disimpan di `etl_ditolak` dengan kode `Q1`–`Q5` (ARCHITECTURE § 7.4). Jangan pernah membuang baris diam-diam.
6. **Angka dashboard berasal dari view SQL.** pandas hanya untuk membentuk data untuk grafik, bukan untuk agregasi utama.
7. **Wilayah adalah pendekatan kotak batas**, diperiksa berurutan (ARCHITECTURE § 7.2). Jangan menyebutnya provinsi atau batas resmi.

---

## Aturan lapisan

```
etl/run.py        →  boleh impor extract, transform, quality, wilayah, load, config
etl/transform.py  →  hanya boleh impor quality, wilayah, config (tanpa jaringan, tanpa DB)
etl/load.py       →  satu-satunya modul yang menulis ke database
dashboard/        →  hanya membaca database lewat dashboard/queries.py
```

- `transform.py`, `quality.py`, `wilayah.py` adalah fungsi murni dan wajib dites.
- SQL file di `sql/` tidak diubah setelah dijalankan; tambahkan file bernomor baru.

---

## Konvensi kode

- Python 3.11, type hints di semua fungsi publik, `dataclass` untuk `BarisGempa` dan `Penolakan`.
- Nama domain bahasa Indonesia (`magnitudo`, `kedalaman_km`, `wilayah`), istilah teknis bahasa Inggris (`upsert`, `staging`, `fixture`).
- Query selalu berparameter (`%s` di psycopg). Tidak ada f-string untuk menyusun SQL berisi input.
- Logging dengan modul `logging`, bukan `print`, di `etl/`.
- Konstanta (BBOX, magnitudo minimum, URL, batas kelas) hanya di `etl/config.py`.

---

## Yang tidak boleh dilakukan

- Menyebut dashboard sebagai sumber informasi darurat atau peringatan gempa.
- Mengklaim data berasal dari BMKG.
- Menghapus atau melemahkan test agar hijau.
- Menyimpan `.env` atau `DATABASE_URL` ke git, termasuk di file workflow.
- Mengubah keputusan di `docs/ARCHITECTURE.md § 10` tanpa membahasnya lebih dulu.

---

## Perintah

```bash
python -m etl.run --mode init                         # jalankan sql/ berurutan
python -m etl.run --mode backfill --mulai 2016-01-01  # isi awal
python -m etl.run --mode inkremental                  # 30 hari terakhir
pytest                                                # test
streamlit run dashboard/app.py                        # dashboard lokal
```

---

## Kesalahan yang sering terjadi

| Gejala | Kemungkinan penyebab |
|---|---|
| Gempa muncul di Samudra Hindia padahal "Jawa" | Lintang dan bujur tertukar saat membaca `coordinates` |
| Jumlah baris bertambah setiap run | Tidak memakai `ON CONFLICT`, atau `event_id` tidak jadi primary key |
| Magnitudo kembali ke nilai lama | Upsert tanpa `WHERE ... diperbarui_pada <` |
| Gempa tengah malam masuk tanggal yang salah | Campur aduk UTC dan WIB saat membuat `tanggal_id` |
| Backfill berhenti di tengah dan semuanya hilang | Commit sekali di akhir, bukan per jendela |
| Request ditolak (429) | Tidak ada jeda/backoff antar-request |
| Dashboard lambat | Query tanpa `st.cache_data` atau agregasi dilakukan di pandas |
