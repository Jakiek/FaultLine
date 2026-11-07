"""Ambil fitur gempa dari USGS FDSN Event API."""

import logging
import time
from datetime import date

import requests

from etl.config import (
    BACKOFF_DETIK,
    BATAS_FITUR_USGS,
    BBOX,
    JEDA_DETIK,
    MAG_MIN,
    TIMEOUT_DETIK,
    USER_AGENT,
    USGS_URL,
)

log = logging.getLogger(__name__)

_sesi = requests.Session()
_sesi.headers["User-Agent"] = USER_AGENT
_request_terakhir = 0.0


class GagalAmbil(RuntimeError):
    """Permintaan ke USGS gagal setelah semua retry."""


def _parameter(mulai: date, selesai: date) -> dict:
    return {
        "format": "geojson",
        "starttime": mulai.isoformat(),   # tanpa zona waktu = UTC menurut USGS
        "endtime": selesai.isoformat(),
        "minmagnitude": MAG_MIN,
        "orderby": "time-asc",            # urutan stabil
        **BBOX,
    }


def _jeda() -> None:
    """Pastikan ada jeda minimum antar-request agar tidak membebani USGS."""
    global _request_terakhir
    sisa = JEDA_DETIK - (time.monotonic() - _request_terakhir)
    if sisa > 0:
        time.sleep(sisa)
    _request_terakhir = time.monotonic()


def ambil_jendela(mulai: date, selesai: date) -> list[dict]:
    """Ambil semua fitur dengan waktu di [mulai, selesai) dalam UTC.

    Retry untuk 429, 5xx, dan galat jaringan dengan backoff 2, 4, 8 detik.
    Status 4xx lain langsung gagal karena mengulang tidak akan membantu.
    """
    params = _parameter(mulai, selesai)
    for percobaan, tunggu in enumerate((*BACKOFF_DETIK, None), start=1):
        _jeda()
        try:
            resp = _sesi.get(USGS_URL, params=params, timeout=TIMEOUT_DETIK)
        except requests.RequestException as e:
            alasan = f"galat jaringan: {e}"
        else:
            if resp.status_code == 200:
                fitur = resp.json().get("features", [])
                if len(fitur) >= BATAS_FITUR_USGS:
                    raise GagalAmbil(
                        f"Jendela {mulai}…{selesai} mencapai batas {BATAS_FITUR_USGS} fitur; perkecil jendela."
                    )
                log.info("USGS %s…%s: %d fitur", mulai, selesai, len(fitur))
                return fitur
            if resp.status_code != 429 and resp.status_code < 500:
                raise GagalAmbil(f"USGS menolak permintaan ({resp.status_code}): {resp.text[:200]}")
            alasan = f"status {resp.status_code}"

        if tunggu is None:
            raise GagalAmbil(f"USGS {mulai}…{selesai} gagal setelah {percobaan} percobaan ({alasan})")
        log.warning("USGS %s…%s %s; coba lagi dalam %d detik", mulai, selesai, alasan, tunggu)
        time.sleep(tunggu)

    raise AssertionError("tidak tercapai")
