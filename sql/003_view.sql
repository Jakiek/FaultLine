-- 003_view.sql — view analitik (ARCHITECTURE § 8) dan view datar untuk dashboard.

-- Fakta yang sudah di-join dengan kedua dimensi. Dashboard mengagregasi view ini
-- dengan WHERE berparameter (tanggal, magnitudo minimum, wilayah); lihat
-- docs/decisions/001_view-datar-untuk-filter.md.
CREATE VIEW v_gempa AS
SELECT f.event_id, f.waktu_utc, d.tanggal, d.tahun, d.bulan, w.nama AS wilayah,
       f.magnitudo, f.kelas_magnitudo, f.kedalaman_km, f.kelas_kedalaman,
       f.lintang, f.bujur, f.tempat, f.tsunami, f.status
FROM fakta_gempa f
JOIN dim_tanggal d USING (tanggal_id)
JOIN dim_wilayah w USING (wilayah_id);

-- Jumlah gempa dan gempa M ≥ 6 per bulan (tanggal UTC) per wilayah.
CREATE VIEW v_gempa_bulanan AS
SELECT d.tahun, d.bulan, w.nama AS wilayah, COUNT(*) AS jumlah,
       COUNT(*) FILTER (WHERE f.magnitudo >= 6) AS jumlah_m6
FROM fakta_gempa f
JOIN dim_tanggal d USING (tanggal_id)
JOIN dim_wilayah w USING (wilayah_id)
GROUP BY d.tahun, d.bulan, w.nama;

-- Jumlah, magnitudo maksimum, dan rata-rata kedalaman per wilayah.
CREATE VIEW v_per_wilayah AS
SELECT w.nama AS wilayah, COUNT(*) AS jumlah, MAX(f.magnitudo) AS magnitudo_maks,
       ROUND(AVG(f.kedalaman_km), 1) AS rata_kedalaman
FROM fakta_gempa f JOIN dim_wilayah w USING (wilayah_id)
GROUP BY w.nama;

-- Histogram magnitudo dengan lebar bin 0,5 (4,0; 4,5; 5,0; …).
CREATE VIEW v_distribusi_magnitudo AS
SELECT FLOOR(magnitudo * 2) / 2 AS bin_magnitudo, COUNT(*) AS jumlah
FROM fakta_gempa GROUP BY 1;

-- Jumlah gempa per kelas kedalaman (dangkal / menengah / dalam).
CREATE VIEW v_kedalaman AS
SELECT kelas_kedalaman, COUNT(*) AS jumlah FROM fakta_gempa GROUP BY 1;

-- 50 gempa terkuat, yang terbaru lebih dulu bila magnitudonya sama.
CREATE VIEW v_terkuat AS
SELECT event_id, waktu_utc, magnitudo, kedalaman_km, tempat, lintang, bujur
FROM fakta_gempa ORDER BY magnitudo DESC, waktu_utc DESC LIMIT 50;

-- Run ETL sukses terakhir, untuk kartu "Run ETL terakhir".
CREATE VIEW v_run_terakhir AS
SELECT * FROM etl_log WHERE status = 'sukses' ORDER BY run_id DESC LIMIT 1;
