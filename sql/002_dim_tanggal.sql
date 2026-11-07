-- 002_dim_tanggal.sql — isi dim_tanggal 2016-01-01 s.d. 2030-12-31 (5.479 hari).

INSERT INTO dim_tanggal (tanggal_id, tanggal, tahun, kuartal, bulan, nama_bulan, hari_minggu)
SELECT
  to_char(t, 'YYYYMMDD')::INT,
  t::DATE,
  EXTRACT(YEAR FROM t)::INT,
  EXTRACT(QUARTER FROM t)::INT,
  EXTRACT(MONTH FROM t)::INT,
  (ARRAY['Januari','Februari','Maret','April','Mei','Juni','Juli',
         'Agustus','September','Oktober','November','Desember'])[EXTRACT(MONTH FROM t)::INT],
  EXTRACT(ISODOW FROM t)::INT
FROM generate_series('2016-01-01'::DATE, '2030-12-31'::DATE, INTERVAL '1 day') AS t;
