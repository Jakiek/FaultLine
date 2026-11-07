"""Semua SQL dashboard. Hanya membaca; setiap query berparameter dan di-cache 10 menit."""

import os
from dataclasses import dataclass
from datetime import date

import pandas as pd
import psycopg
import streamlit as st

WILAYAH = (
    "Sumatra", "Jawa", "Bali & Nusa Tenggara", "Kalimantan",
    "Sulawesi", "Maluku", "Papua", "Lainnya",
)


@dataclass(frozen=True)
class Filter:
    mulai: date
    akhir: date
    magnitudo_min: float
    wilayah: tuple[str, ...]

    def params(self) -> dict:
        return {
            "mulai": self.mulai,
            "akhir": self.akhir,
            "mag": self.magnitudo_min,
            "wilayah": list(self.wilayah),
        }


# Fragmen tetap (bukan input pengguna); nilai filter selalu lewat parameter.
_WHERE = """
WHERE tanggal BETWEEN %(mulai)s AND %(akhir)s
  AND magnitudo >= %(mag)s
  AND wilayah = ANY(%(wilayah)s)
"""


def _url() -> str:
    try:
        url = st.secrets.get("DATABASE_URL")
    except Exception:  # tidak ada secrets.toml saat lokal
        url = None
    url = url or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL belum diatur")
    return url


def _baca(sql: str, params: dict | None = None) -> pd.DataFrame:
    with psycopg.connect(_url(), connect_timeout=10) as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        kolom = [d.name for d in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=kolom)


@st.cache_data(ttl=600, show_spinner=False)
def rentang_data() -> tuple[date | None, date | None]:
    df = _baca("SELECT MIN(tanggal) AS awal, MAX(tanggal) AS akhir FROM v_gempa")
    return df.at[0, "awal"], df.at[0, "akhir"]


@st.cache_data(ttl=600, show_spinner=False)
def ringkasan(f: Filter) -> pd.Series:
    return _baca(
        "SELECT COUNT(*) AS total,"
        " COUNT(*) FILTER (WHERE magnitudo >= 6) AS jumlah_m6,"
        " AVG(kedalaman_km)::float8 AS rata_kedalaman"
        " FROM v_gempa" + _WHERE,
        f.params(),
    ).iloc[0]


@st.cache_data(ttl=600, show_spinner=False)
def run_terakhir() -> pd.DataFrame:
    """Tidak terpengaruh filter (DESIGN § 2)."""
    return _baca("SELECT run_id, mode, selesai, jumlah_insert, jumlah_update, jumlah_ditolak FROM v_run_terakhir")


@st.cache_data(ttl=600, show_spinner=False)
def tren_bulanan(f: Filter) -> pd.DataFrame:
    return _baca(
        "SELECT make_date(tahun, bulan, 1) AS bulan, COUNT(*) AS jumlah,"
        " COUNT(*) FILTER (WHERE magnitudo >= 6) AS jumlah_m6"
        " FROM v_gempa" + _WHERE + " GROUP BY 1 ORDER BY 1",
        f.params(),
    )


@st.cache_data(ttl=600, show_spinner=False)
def titik_peta(f: Filter, batas: int) -> pd.DataFrame:
    return _baca(
        "SELECT lintang::float8 AS lintang, bujur::float8 AS bujur, magnitudo::float8 AS magnitudo,"
        " kedalaman_km::float8 AS kedalaman_km, tempat, waktu_utc"
        " FROM v_gempa" + _WHERE + " ORDER BY magnitudo DESC, waktu_utc DESC LIMIT %(batas)s",
        {**f.params(), "batas": batas},
    )


@st.cache_data(ttl=600, show_spinner=False)
def distribusi_magnitudo(f: Filter) -> pd.DataFrame:
    return _baca(
        "SELECT (FLOOR(magnitudo * 2) / 2)::float8 AS bin_magnitudo, COUNT(*) AS jumlah"
        " FROM v_gempa" + _WHERE + " GROUP BY 1 ORDER BY 1",
        f.params(),
    )


@st.cache_data(ttl=600, show_spinner=False)
def per_wilayah(f: Filter) -> pd.DataFrame:
    return _baca(
        "SELECT wilayah, COUNT(*) AS jumlah, MAX(magnitudo)::float8 AS magnitudo_maks"
        " FROM v_gempa" + _WHERE + " GROUP BY wilayah ORDER BY jumlah DESC, wilayah",
        f.params(),
    )


@st.cache_data(ttl=600, show_spinner=False)
def kedalaman(f: Filter) -> pd.DataFrame:
    return _baca(
        "SELECT kelas_kedalaman, COUNT(*) AS jumlah FROM v_gempa" + _WHERE +
        " GROUP BY 1 ORDER BY array_position(ARRAY['dangkal','menengah','dalam'], kelas_kedalaman)",
        f.params(),
    )


@st.cache_data(ttl=600, show_spinner=False)
def terkuat(f: Filter, batas: int = 10) -> pd.DataFrame:
    return _baca(
        "SELECT waktu_utc, magnitudo::float8 AS magnitudo, kedalaman_km::float8 AS kedalaman_km,"
        " wilayah, tempat, event_id"
        " FROM v_gempa" + _WHERE + " ORDER BY magnitudo DESC, waktu_utc DESC LIMIT %(batas)s",
        {**f.params(), "batas": batas},
    )
