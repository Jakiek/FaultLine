-- 001_skema.sql — star schema gudang data gempa, staging mentah, dan log ETL.
--
-- Semua waktu disimpan dalam UTC (TIMESTAMPTZ). tanggal_id di fakta_gempa
-- diturunkan dari tanggal UTC, bukan WIB: data sumber USGS memakai UTC, dan
-- satu acuan zona waktu membuat join ke dim_tanggal konsisten. Konversi ke WIB
-- hanya dilakukan di dashboard.

-- Respons mentah USGS per fitur, disimpan apa adanya agar transform bisa
-- diulang tanpa memanggil API lagi. ETL tidak pernah menghapus tabel ini.
CREATE TABLE stg_gempa_mentah (
  event_id      TEXT        NOT NULL,
  payload       JSONB       NOT NULL,
  diambil_pada  TIMESTAMPTZ NOT NULL DEFAULT now(),
  run_id        INT         NOT NULL,
  PRIMARY KEY (event_id, run_id)
);

CREATE TABLE dim_tanggal (
  tanggal_id   INT  PRIMARY KEY,           -- YYYYMMDD
  tanggal      DATE NOT NULL UNIQUE,
  tahun        INT  NOT NULL,
  kuartal      INT  NOT NULL,
  bulan        INT  NOT NULL,
  nama_bulan   TEXT NOT NULL,              -- 'Januari', ...
  hari_minggu  INT  NOT NULL               -- 1 = Senin
);

-- Wilayah adalah pendekatan kotak batas (lihat etl/wilayah.py), bukan batas
-- administratif. wilayah_id mengikuti urutan pemeriksaan kotak.
CREATE TABLE dim_wilayah (
  wilayah_id  SERIAL PRIMARY KEY,
  nama        TEXT NOT NULL UNIQUE
);

INSERT INTO dim_wilayah (nama) VALUES
  ('Jawa'),
  ('Bali & Nusa Tenggara'),
  ('Sumatra'),
  ('Kalimantan'),
  ('Sulawesi'),
  ('Papua'),
  ('Maluku'),
  ('Lainnya');

CREATE TABLE fakta_gempa (
  event_id          TEXT PRIMARY KEY,      -- id USGS, mis. 'us7000abcd'
  tanggal_id        INT  NOT NULL REFERENCES dim_tanggal(tanggal_id),
  wilayah_id        INT  NOT NULL REFERENCES dim_wilayah(wilayah_id),
  waktu_utc         TIMESTAMPTZ NOT NULL,
  magnitudo         NUMERIC(3,1) NOT NULL,
  tipe_magnitudo    TEXT,
  kelas_magnitudo   TEXT NOT NULL CHECK (kelas_magnitudo IN ('ringan','sedang','kuat','besar')),
  kedalaman_km      NUMERIC(6,2) NOT NULL,
  kelas_kedalaman   TEXT NOT NULL CHECK (kelas_kedalaman IN ('dangkal','menengah','dalam')),
  lintang           NUMERIC(7,4) NOT NULL,
  bujur             NUMERIC(7,4) NOT NULL,
  tempat            TEXT,                  -- teks asli USGS
  di_indonesia      BOOLEAN NOT NULL,      -- tempat diakhiri 'Indonesia'
  signifikansi      INT,
  tsunami           BOOLEAN NOT NULL,
  status            TEXT NOT NULL,         -- 'automatic' | 'reviewed'
  diperbarui_pada   TIMESTAMPTZ NOT NULL,  -- properti 'updated' dari USGS
  dimuat_pada       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ON fakta_gempa (tanggal_id);
CREATE INDEX ON fakta_gempa (wilayah_id);
CREATE INDEX ON fakta_gempa (magnitudo);

CREATE TABLE etl_log (
  run_id          SERIAL PRIMARY KEY,
  mode            TEXT NOT NULL,
  mulai           TIMESTAMPTZ NOT NULL DEFAULT now(),
  selesai         TIMESTAMPTZ,
  rentang_awal    DATE NOT NULL,
  rentang_akhir   DATE NOT NULL,
  jumlah_diambil  INT DEFAULT 0,
  jumlah_insert   INT DEFAULT 0,
  jumlah_update   INT DEFAULT 0,
  jumlah_ditolak  INT DEFAULT 0,
  status          TEXT NOT NULL DEFAULT 'berjalan'
                  CHECK (status IN ('berjalan','sukses','gagal')),
  pesan           TEXT
);

-- Baris yang ditolak aturan kualitas Q1–Q5; alasan diawali kode aturannya.
CREATE TABLE etl_ditolak (
  run_id    INT  NOT NULL REFERENCES etl_log(run_id),
  event_id  TEXT,
  alasan    TEXT NOT NULL,
  payload   JSONB NOT NULL
);

CREATE INDEX ON etl_ditolak (run_id);
