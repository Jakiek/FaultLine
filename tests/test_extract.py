"""Retry dan backoff extract, tanpa jaringan sungguhan."""

from datetime import date

import pytest
import requests

from etl import extract


class _Respons:
    def __init__(self, status: int, fitur: list | None = None):
        self.status_code = status
        self.text = "galat"
        self._fitur = fitur or []

    def json(self):
        return {"features": self._fitur}


@pytest.fixture
def tidur(monkeypatch):
    jeda: list[float] = []
    monkeypatch.setattr(extract.time, "sleep", jeda.append)
    return jeda


def _pasang(monkeypatch, urutan):
    panggilan = []

    def get(url, params, timeout):
        panggilan.append(params)
        hasil = urutan.pop(0)
        if isinstance(hasil, Exception):
            raise hasil
        return hasil

    monkeypatch.setattr(extract._sesi, "get", get)
    return panggilan


def test_parameter_tetap_dan_urutan_waktu(monkeypatch, tidur):
    panggilan = _pasang(monkeypatch, [_Respons(200, [{"id": "a"}])])
    assert extract.ambil_jendela(date(2024, 1, 1), date(2024, 2, 1)) == [{"id": "a"}]
    p = panggilan[0]
    assert p["orderby"] == "time-asc"
    assert (p["starttime"], p["endtime"]) == ("2024-01-01", "2024-02-01")
    assert (p["minlatitude"], p["maxlongitude"], p["minmagnitude"]) == (-11.0, 141.0, 4.0)


def test_retry_429_lalu_galat_jaringan_lalu_sukses(monkeypatch, tidur):
    _pasang(monkeypatch, [_Respons(429), requests.ConnectionError("putus"), _Respons(200, [])])
    assert extract.ambil_jendela(date(2024, 1, 1), date(2024, 2, 1)) == []
    assert [t for t in tidur if t >= 2] == [2, 4]   # backoff, di luar jeda antar-request


def test_menyerah_setelah_empat_percobaan(monkeypatch, tidur):
    _pasang(monkeypatch, [_Respons(503)] * 4)
    with pytest.raises(extract.GagalAmbil, match="4 percobaan"):
        extract.ambil_jendela(date(2024, 1, 1), date(2024, 2, 1))


def test_400_langsung_gagal_tanpa_retry(monkeypatch, tidur):
    panggilan = _pasang(monkeypatch, [_Respons(400)])
    with pytest.raises(extract.GagalAmbil, match="400"):
        extract.ambil_jendela(date(2024, 1, 1), date(2024, 2, 1))
    assert len(panggilan) == 1
