# ADR 001 — View datar `v_gempa` untuk filter dashboard

Status: diterima · 7 November 2026

## Konteks

ARCHITECTURE § 8 menetapkan enam view agregat, misalnya `v_per_wilayah` dan `v_distribusi_magnitudo`. View tersebut sudah dikelompokkan, sehingga kolom tanggal dan magnitudo per baris tidak lagi tersedia. Dashboard membutuhkan filter rentang tanggal, magnitudo minimum, dan wilayah (US-5) yang memengaruhi semua visual. Filter tersebut tidak dapat diterapkan sebagai `WHERE` di atas view yang sudah teragregasi.

Pilihan yang ditimbang:

1. Mengambil baris mentah lalu mengagregasi dengan pandas. Ditolak karena melanggar aturan "angka dashboard berasal dari SQL".
2. Membuat satu view agregat per kombinasi filter. Ditolak karena rentang tanggal dan ambang magnitudo bersifat kontinu.
3. **Menambah view datar `v_gempa`**, yaitu `fakta_gempa` yang di-join dengan `dim_tanggal` dan `dim_wilayah`. Query dashboard di `dashboard/queries.py` mengagregasinya dengan `GROUP BY` dan `WHERE` berparameter.

## Keputusan

Pilihan 3. Seluruh agregasi tetap dikerjakan PostgreSQL. pandas hanya membentuk data untuk grafik, misalnya label bin dan format WIB. Enam view di § 8 tetap dibuat untuk analisis SQL langsung tanpa filter. `v_run_terakhir` dipakai apa adanya oleh kartu "Run ETL terakhir", yang memang tidak terpengaruh filter.

Filter tanggal memakai kolom `tanggal` dari `dim_tanggal`, yaitu tanggal UTC, konsisten dengan `tanggal_id`. Label filter di dashboard menyebut "UTC". Waktu kejadian tetap ditampilkan dalam WIB.

## Konsekuensi

- Logika join dimensi ditulis sekali di view, bukan diulang di setiap query.
- Dengan sekitar puluhan ribu baris, agregasi langsung tetap cepat. Hasil query di-cache 10 menit dengan `st.cache_data`.
- Bila data tumbuh jauh lebih besar, view agregat harian (misalnya per tanggal × wilayah × bin magnitudo) dapat menggantikan `v_gempa` tanpa mengubah tampilan.
