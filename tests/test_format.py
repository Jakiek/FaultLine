from datetime import UTC, datetime

from dashboard.format import angka, desimal, waktu_wib


def test_angka_pemisah_ribuan_titik():
    assert angka(1234567) == "1.234.567"
    assert angka(0) == "0"


def test_desimal_koma():
    assert desimal(5.66) == "5,7"
    assert desimal(7.0) == "7,0"
    assert desimal(1234.6, 0) == "1.235"


def test_waktu_wib_tujuh_jam_di_depan_utc():
    # 20:30 UTC 31 Des = 03:30 WIB 1 Jan tahun berikutnya.
    assert waktu_wib(datetime(2023, 12, 31, 20, 30, tzinfo=UTC)) == "01-01-2024 03:30 WIB"
