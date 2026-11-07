"""Konstanta pipeline. Satu-satunya tempat untuk BBOX, ambang, URL, dan batas kelas."""

from datetime import date
from pathlib import Path

# --- Sumber data USGS (ARCHITECTURE § 5) ---
USGS_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
USER_AGENT = "faultline-portfolio (github.com/Jakiek)"
MAG_MIN = 4.0

# Kotak batas Indonesia, dipakai sebagai parameter query dan aturan Q4.
BBOX = {
    "minlatitude": -11.0,
    "maxlatitude": 6.0,
    "minlongitude": 95.0,
    "maxlongitude": 141.0,
}

JEDA_DETIK = 1.0                 # jeda minimum antar-request
BACKOFF_DETIK = (2, 4, 8)        # retry untuk status 429 / 5xx / galat jaringan
TIMEOUT_DETIK = 60
BATAS_FITUR_USGS = 20_000        # batas fitur per request dari USGS

JENDELA_INKREMENTAL_HARI = 30
# dim_tanggal hanya berisi 2016-01-01 s.d. 2030-12-31 (sql/002_dim_tanggal.sql).
TANGGAL_MIN = date(2016, 1, 1)
TANGGAL_MAKS = date(2030, 12, 31)

# --- Aturan kualitas (ARCHITECTURE § 7.4) ---
KEDALAMAN_MIN_KM = -5.0
KEDALAMAN_MAKS_KM = 800.0
TIPE_DITERIMA = "earthquake"

# --- Kelas (ARCHITECTURE § 7.3) ---
# Kedalaman: dangkal < 70, menengah 70–300 (inklusif), dalam > 300.
BATAS_DANGKAL_KM = 70.0
BATAS_DALAM_KM = 300.0

# Magnitudo: (ambang bawah inklusif, nama kelas), dari yang terbesar.
KELAS_MAGNITUDO = (
    (7.0, "besar"),
    (6.0, "kuat"),
    (5.0, "sedang"),
    (MAG_MIN, "ringan"),
)

# --- Wilayah kotak batas, diperiksa berurutan (ARCHITECTURE § 7.2) ---
# (nama, bujur_min, bujur_maks, lintang_min, lintang_maks)
KOTAK_WILAYAH = (
    ("Jawa", 105.0, 115.0, -9.5, -5.5),
    ("Bali & Nusa Tenggara", 114.4, 127.5, -11.0, -7.5),
    ("Sumatra", 95.0, 106.5, -6.5, 6.0),
    ("Kalimantan", 108.5, 119.0, -4.5, 5.0),
    ("Sulawesi", 118.5, 125.5, -6.5, 2.5),
    ("Papua", 130.5, 141.0, -9.5, 1.0),
    ("Maluku", 124.0, 135.0, -8.5, 3.0),
)
WILAYAH_LAINNYA = "Lainnya"

FOLDER_SQL = Path(__file__).resolve().parent.parent / "sql"
