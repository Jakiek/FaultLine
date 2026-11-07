from datetime import UTC, datetime
from decimal import Decimal

import pytest

from etl.quality import Penolakan
from etl.transform import (
    BarisGempa,
    kelas_kedalaman,
    kelas_magnitudo,
    ms_ke_utc,
    ubah_batch,
    ubah_fitur,
)
from tests.conftest import buat_fitur


def test_ms_ke_utc_tepat_sampai_milidetik():
    assert ms_ke_utc(1_704_070_759_656) == datetime(2024, 1, 1, 0, 59, 19, 656_000, tzinfo=UTC)


def test_koordinat_geojson_bujur_dulu(fitur_normal):
    # Fixture asli: coordinates = [107.1224, -6.8599, 178.051] (Cianjur)
    baris = ubah_fitur(fitur_normal)
    assert isinstance(baris, BarisGempa)
    assert baris.bujur == Decimal("107.1224")
    assert baris.lintang == Decimal("-6.8599")
    assert baris.kedalaman_km == Decimal("178.05")
    assert baris.wilayah == "Jawa"


def test_fitur_asli_dipetakan_lengkap(fitur_normal):
    baris = ubah_fitur(fitur_normal)
    assert baris.event_id == "us6000m0wb"
    assert baris.magnitudo == Decimal("4.1")
    assert baris.kelas_magnitudo == "ringan"
    assert baris.kelas_kedalaman == "menengah"
    assert baris.di_indonesia is True
    assert baris.tsunami is False
    assert baris.status == "reviewed"
    assert baris.diperbarui_pada == ms_ke_utc(1_710_020_291_040)


def test_tanggal_id_dari_tanggal_utc_bukan_wib():
    # 2024-01-01 20:00 UTC = 2024-01-02 03:00 WIB → tetap 20240101.
    ms = int(datetime(2024, 1, 1, 20, 0, tzinfo=UTC).timestamp() * 1000)
    assert ubah_fitur(buat_fitur(time=ms)).tanggal_id == 20240101


@pytest.mark.parametrize(
    ("kedalaman", "kelas"),
    [(69.9, "dangkal"), (70, "menengah"), (300, "menengah"), (300.1, "dalam")],
)
def test_kelas_kedalaman_di_batas(kedalaman, kelas):
    assert kelas_kedalaman(kedalaman) == kelas


@pytest.mark.parametrize(
    ("magnitudo", "kelas"),
    [(4.0, "ringan"), (4.9, "ringan"), (5.0, "sedang"), (5.9, "sedang"),
     (6.0, "kuat"), (6.9, "kuat"), (7.0, "besar"), (8.2, "besar")],
)
def test_kelas_magnitudo_di_batas(magnitudo, kelas):
    assert kelas_magnitudo(magnitudo) == kelas


def test_kelas_mengikuti_nilai_yang_dibulatkan():
    # 4,95 tersimpan sebagai NUMERIC(3,1) = 5,0 → kelasnya harus 'sedang', bukan 'ringan'.
    baris = ubah_fitur(buat_fitur(mag=4.95))
    assert baris.magnitudo == Decimal("5.0")
    assert baris.kelas_magnitudo == "sedang"


def test_quarry_blast_ditolak_q2(fitur_usgs):
    hasil = ubah_fitur(fitur_usgs[1])
    assert isinstance(hasil, Penolakan)
    assert hasil.kode == "Q2"
    assert hasil.alasan.startswith("Q2: ")
    assert hasil.event_id == "us6000m356"


def test_tanpa_magnitudo_ditolak_q1(fitur_usgs):
    hasil = ubah_fitur(fitur_usgs[2])
    assert isinstance(hasil, Penolakan) and hasil.kode == "Q1"


def test_batch_fixture_satu_lolos_dua_ditolak(fitur_usgs):
    baris, ditolak = ubah_batch(fitur_usgs)
    assert [b.event_id for b in baris] == ["us6000m0wb"]
    assert sorted(p.kode for p in ditolak) == ["Q1", "Q2"]


def test_duplikat_dalam_batch_yang_terbaru_menang_q5():
    lama = buat_fitur(event_id="dup", mag=5.0, updated=1_000)
    baru = buat_fitur(event_id="dup", mag=5.4, updated=2_000)
    baris, ditolak = ubah_batch([baru, lama])   # urutan masuk tidak berpengaruh
    assert len(baris) == 1 and baris[0].magnitudo == Decimal("5.4")
    assert [p.kode for p in ditolak] == ["Q5"]
    assert ditolak[0].payload["properties"]["updated"] == 1_000
