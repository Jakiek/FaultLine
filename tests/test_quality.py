import pytest

from etl.quality import periksa_fitur, pilih_terbaru
from tests.conftest import buat_fitur


def test_fitur_valid_lolos():
    assert periksa_fitur(buat_fitur()) is None


@pytest.mark.parametrize(
    "ubah",
    [
        lambda f: f["properties"].update(mag=None),
        lambda f: f["geometry"].update(coordinates=[110.0, None, 10.0]),
        lambda f: f["geometry"].update(coordinates=[110.0, -7.0]),
        lambda f: f.update(geometry=None),
        lambda f: f["properties"].update(updated=None),
        lambda f: f.update(id=None),
    ],
    ids=["mag-kosong", "lintang-kosong", "kedalaman-hilang", "geometry-null", "updated-kosong", "id-kosong"],
)
def test_field_wajib_kosong_q1(ubah):
    fitur = buat_fitur()
    ubah(fitur)
    assert periksa_fitur(fitur).kode == "Q1"


@pytest.mark.parametrize("tipe", ["quarry blast", "explosion", "volcanic eruption", None])
def test_tipe_bukan_earthquake_q2(tipe):
    assert periksa_fitur(buat_fitur(tipe=tipe)).kode == "Q2"


@pytest.mark.parametrize(("kedalaman", "ditolak"), [(-5.1, True), (-5, False), (800, False), (800.1, True)])
def test_batas_kedalaman_q3(kedalaman, ditolak):
    hasil = periksa_fitur(buat_fitur(kedalaman=kedalaman))
    assert (hasil is not None and hasil.kode == "Q3") is ditolak


@pytest.mark.parametrize(("bujur", "lintang"), [(94.9, 0.0), (141.1, -5.0), (120.0, 6.1), (120.0, -11.1)])
def test_di_luar_kotak_indonesia_q4(bujur, lintang):
    assert periksa_fitur(buat_fitur(bujur=bujur, lintang=lintang)).kode == "Q4"


def test_q1_diperiksa_sebelum_q2():
    # Fitur dengan dua pelanggaran dicatat dengan aturan pertama.
    assert periksa_fitur(buat_fitur(mag=None, tipe="explosion")).kode == "Q1"


def test_q5_seri_updated_menyimpan_yang_terakhir():
    a = buat_fitur(event_id="x", mag=5.0, updated=10)
    b = buat_fitur(event_id="x", mag=5.1, updated=10)
    unik, tersisih = pilih_terbaru([a, b])
    assert unik == [b]
    assert [p.kode for p in tersisih] == ["Q5"]


def test_q5_tiga_versi_dua_dicatat():
    versi = [buat_fitur(event_id="x", updated=u) for u in (30, 10, 20)]
    unik, tersisih = pilih_terbaru(versi)
    assert unik[0]["properties"]["updated"] == 30
    assert sorted(p.payload["properties"]["updated"] for p in tersisih) == [10, 20]


def test_q5_fitur_tanpa_id_tidak_digabung():
    unik, tersisih = pilih_terbaru([buat_fitur(event_id=None), buat_fitur(event_id=None)])
    assert len(unik) == 2 and tersisih == []
