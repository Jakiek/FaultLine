# ARCHITECTURE — Faultline

## 1. Prinsip arsitektur

1. **Idempoten.** Menjalankan ETL berkali-kali untuk rentang yang sama menghasilkan isi gudang data yang sama.
2. **Data mentah tidak pernah dibuang.** Respons API disimpan di staging agar transform bisa diulang tanpa memanggil API lagi.
3. **Transform adalah fungsi murni.** `etl/transform.py` tidak menyentuh jaringan atau database, sehingga mudah dites.
4. **Waktu disimpan dalam UTC**, dikonversi ke WIB hanya di lapisan tampilan.
5. **Angka dashboard berasal dari view SQL.**

## 2. Alur data

```
USGS FDSN API ──extract──▶ stg_gempa_mentah (JSONB)
                                 │
                             transform  ──tolak──▶ etl_ditolak
                                 │
                               load (upsert)
                                 ▼
             dim_tanggal ◀── fakta_gempa ──▶ dim_wilayah
                                 │
                            view analitik
                                 ▼
                        Dashboard Streamlit
```

Penjadwalan: GitHub Actions (cron harian) → `python -m etl.run --mode inkremental`.

## 3. Stack

| Bagian | Pilihan |
|---|---|
| Bahasa | Python 3.11+ |
| HTTP | `requests` (retry + backoff) |
| Database | PostgreSQL di Neon, driver `psycopg` v3 |
| Dashboard | Streamlit + Plotly + pandas |
| Test | pytest |
| Jadwal | GitHub Actions (`schedule` + `workflow_dispatch`) |
| Hosting dashboard | Streamlit Community Cloud |

## 4. Struktur folder

```
faultline/
├── PROJECTBRIEF.md
├── README.md
├── requirements.txt
├── .env.example                 # DATABASE_URL=
├── docs/
│   ├── ARCHITECTURE.md
│   ├── CONVENTIONS.md           # aturan domain, lapisan, dan konvensi kode
│   ├── DESIGN.md
│   └── ROADMAP.md
├── sql/
│   ├── 001_skema.sql
│   ├── 002_dim_tanggal.sql      # isi dim_tanggal 2016–2030
│   └── 003_view.sql
├── etl/
│   ├── __init__.py
│   ├── config.py                # konstanta: BBOX, MAG_MIN, URL, kelas
│   ├── extract.py               # ambil_jendela(mulai, selesai) -> list[dict]
│   ├── transform.py             # ubah_fitur(fitur) -> BarisGempa | Penolakan
│   ├── quality.py               # aturan validasi
│   ├── wilayah.py               # tentukan_wilayah(lintang, bujur) -> str
│   ├── load.py                  # simpan_mentah, upsert_fakta, simpan_ditolak, catat_log
│   └── run.py                   # CLI: --mode backfill|inkremental
├── dashboard/
│   ├── app.py
│   ├── queries.py               # semua SQL dashboard di satu tempat
│   └── format.py                # format angka/waktu Indonesia
├── tests/
│   ├── fixtures/usgs_contoh.json
│   ├── test_transform.py
│   ├── test_quality.py
│   ├── test_wilayah.py
│   ├── test_extract.py          # retry/backoff tanpa jaringan
│   ├── test_load.py             # integrasi PostgreSQL (TEST_DATABASE_URL)
│   ├── test_run.py
│   └── test_format.py
├── .streamlit/config.toml
└── .github/workflows/etl-harian.yml
```

## 5. Extract — `etl/extract.py`

Endpoint: `https://earthquake.usgs.gov/fdsnws/event/1/query`

Parameter tetap:

```
format=geojson
minlatitude=-11  maxlatitude=6
minlongitude=95  maxlongitude=141
minmagnitude=4.0
orderby=time-asc
```

- **Backfill**: jendela per bulan dari `--mulai` sampai hari ini.
- **Inkremental**: satu jendela, 30 hari terakhir (menangkap revisi data baru).
- Jeda 1 detik antar-request; retry 3× dengan backoff (2, 4, 8 detik) untuk status 429/5xx.
- Header `User-Agent: faultline-portfolio (github.com/Jakiek)`.
- Setiap fitur disimpan ke `stg_gempa_mentah` sebelum ditransform.

## 6. Model data

### 6.1 Skema — `sql/001_skema.sql`

```sql
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

CREATE TABLE dim_wilayah (
  wilayah_id  SERIAL PRIMARY KEY,
  nama        TEXT NOT NULL UNIQUE         -- 'Sumatra', 'Jawa', ..., 'Lainnya'
);

CREATE TABLE fakta_gempa (
  event_id          TEXT PRIMARY KEY,      -- id USGS, mis. 'us7000abcd'
  tanggal_id        INT  NOT NULL REFERENCES dim_tanggal(tanggal_id),
  wilayah_id        INT  NOT NULL REFERENCES dim_wilayah(wilayah_id),
  waktu_utc         TIMESTAMPTZ NOT NULL,
  magnitudo         NUMERIC(3,1) NOT NULL,
  tipe_magnitudo    TEXT,
  kelas_magnitudo   TEXT NOT NULL,         -- lihat § 7.3
  kedalaman_km      NUMERIC(6,2) NOT NULL,
  kelas_kedalaman   TEXT NOT NULL,         -- 'dangkal' | 'menengah' | 'dalam'
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
  status          TEXT NOT NULL DEFAULT 'berjalan',   -- 'berjalan' | 'sukses' | 'gagal'
  pesan           TEXT
);

CREATE TABLE etl_ditolak (
  run_id    INT  NOT NULL REFERENCES etl_log(run_id),
  event_id  TEXT,
  alasan    TEXT NOT NULL,
  payload   JSONB NOT NULL
);
```

### 6.2 Upsert — `etl/load.py`

```sql
INSERT INTO fakta_gempa (...) VALUES (...)
ON CONFLICT (event_id) DO UPDATE SET
  magnitudo = EXCLUDED.magnitudo,
  ...,
  diperbarui_pada = EXCLUDED.diperbarui_pada,
  dimuat_pada = now()
WHERE fakta_gempa.diperbarui_pada < EXCLUDED.diperbarui_pada
RETURNING (xmax = 0) AS baru;
```

`RETURNING (xmax = 0)` bernilai `true` untuk insert dan `false` untuk update — dipakai menghitung `jumlah_insert` dan `jumlah_update`. Klausa `WHERE` mencegah data lama menimpa data yang lebih baru.

## 7. Transform — `etl/transform.py`

### 7.1 Pemetaan field

| GeoJSON USGS | Kolom |
|---|---|
| `id` | `event_id` |
| `properties.time` (ms) | `waktu_utc` |
| `properties.updated` (ms) | `diperbarui_pada` |
| `properties.mag`, `magType` | `magnitudo`, `tipe_magnitudo` |
| `geometry.coordinates[0..2]` | `bujur`, `lintang`, `kedalaman_km` |
| `properties.place` | `tempat`, `di_indonesia` |
| `properties.sig`, `tsunami`, `status`, `type` | kolom terkait |

### 7.2 Wilayah — `etl/wilayah.py` (pendekatan kotak batas)

Diperiksa **berurutan**; yang pertama cocok dipakai.

| Urutan | Wilayah | Bujur | Lintang |
|---|---|---|---|
| 1 | Jawa | 105.0 – 115.0 | −9.5 – −5.5 |
| 2 | Bali & Nusa Tenggara | 114.4 – 127.5 | −11.0 – −7.5 |
| 3 | Sumatra | 95.0 – 106.5 | −6.5 – 6.0 |
| 4 | Kalimantan | 108.5 – 119.0 | −4.5 – 5.0 |
| 5 | Sulawesi | 118.5 – 125.5 | −6.5 – 2.5 |
| 6 | Papua | 130.5 – 141.0 | −9.5 – 1.0 |
| 7 | Maluku | 124.0 – 135.0 | −8.5 – 3.0 |
| 8 | Lainnya | sisanya | |

Ini **bukan batas administratif**. Kolom `tempat` dari USGS tetap disimpan sebagai pembanding.

### 7.3 Kelas

- Kedalaman: `dangkal` < 70 km, `menengah` 70–300 km, `dalam` > 300 km.
- Magnitudo: `4.0–4.9 ringan`, `5.0–5.9 sedang`, `6.0–6.9 kuat`, `≥ 7.0 besar`.

### 7.4 Aturan kualitas — `etl/quality.py`

| Kode | Aturan | Tindakan |
|---|---|---|
| `Q1` | `mag` atau koordinat kosong | Tolak |
| `Q2` | `type` bukan `earthquake` | Tolak |
| `Q3` | Kedalaman < −5 atau > 800 km | Tolak |
| `Q4` | Koordinat di luar kotak Indonesia | Tolak |
| `Q5` | `event_id` muncul dua kali dalam satu batch | Simpan yang `updated`-nya terbaru |

Setiap penolakan disimpan di `etl_ditolak` dengan kode aturannya.

## 8. View analitik — `sql/003_view.sql`

```sql
CREATE VIEW v_gempa_bulanan AS
SELECT d.tahun, d.bulan, w.nama AS wilayah, COUNT(*) AS jumlah,
       COUNT(*) FILTER (WHERE f.magnitudo >= 6) AS jumlah_m6
FROM fakta_gempa f
JOIN dim_tanggal d USING (tanggal_id)
JOIN dim_wilayah w USING (wilayah_id)
GROUP BY d.tahun, d.bulan, w.nama;

CREATE VIEW v_per_wilayah AS
SELECT w.nama AS wilayah, COUNT(*) AS jumlah, MAX(f.magnitudo) AS magnitudo_maks,
       ROUND(AVG(f.kedalaman_km), 1) AS rata_kedalaman
FROM fakta_gempa f JOIN dim_wilayah w USING (wilayah_id)
GROUP BY w.nama;

CREATE VIEW v_distribusi_magnitudo AS
SELECT FLOOR(magnitudo * 2) / 2 AS bin_magnitudo, COUNT(*) AS jumlah
FROM fakta_gempa GROUP BY 1;

CREATE VIEW v_kedalaman AS
SELECT kelas_kedalaman, COUNT(*) AS jumlah FROM fakta_gempa GROUP BY 1;

CREATE VIEW v_terkuat AS
SELECT event_id, waktu_utc, magnitudo, kedalaman_km, tempat, lintang, bujur
FROM fakta_gempa ORDER BY magnitudo DESC, waktu_utc DESC LIMIT 50;

CREATE VIEW v_run_terakhir AS
SELECT * FROM etl_log WHERE status = 'sukses' ORDER BY run_id DESC LIMIT 1;
```

Dashboard tetap boleh menambahkan `WHERE` untuk filter (tanggal, magnitudo minimum, wilayah) — dengan parameter, bukan string concatenation.

Karena view di atas sudah teragregasi, filter diterapkan pada view datar `v_gempa` (fakta + kedua dimensi) dan diagregasi di SQL oleh `dashboard/queries.py`. Lihat [ADR 001](decisions/001_view-datar-untuk-filter.md).

## 9. Penjadwalan — `.github/workflows/etl-harian.yml`

```yaml
on:
  schedule: [{ cron: "0 1 * * *" }]   # 08.00 WIB
  workflow_dispatch: {}
jobs:
  etl:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r requirements.txt
      - run: python -m etl.run --mode inkremental
        env: { DATABASE_URL: "${{ secrets.DATABASE_URL }}" }
```

## 10. Keputusan yang dikunci

1. Sumber data hanya USGS; magnitudo minimum 4.0; kotak Indonesia seperti § 5.
2. Waktu disimpan UTC; tampilan WIB.
3. Load selalu upsert berdasarkan `event_id` dengan pemeriksaan `diperbarui_pada`.
4. Staging mentah tidak dihapus oleh ETL.
5. Wilayah memakai kotak batas § 7.2 dan dinyatakan sebagai pendekatan.

Perubahan keputusan dicatat sebagai ADR di `docs/decisions/`.
