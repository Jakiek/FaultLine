import pytest

from etl.wilayah import tentukan_wilayah


@pytest.mark.parametrize(
    ("lintang", "bujur", "wilayah"),
    [
        (-6.2, 106.8, "Jawa"),                     # Jakarta
        (-6.0, 105.5, "Jawa"),                     # Selat Sunda: Jawa diperiksa sebelum Sumatra
        (-8.65, 115.2, "Bali & Nusa Tenggara"),    # Denpasar: bujur 115,2 sudah di luar kotak Jawa
        (3.6, 98.7, "Sumatra"),                    # Medan
        (-0.5, 117.1, "Kalimantan"),               # Samarinda
        (-5.1, 119.4, "Sulawesi"),                 # Makassar
        (-2.5, 140.7, "Papua"),                    # Jayapura
        (-3.7, 128.2, "Maluku"),                   # Ambon
        (-6.0, 128.0, "Maluku"),                   # Laut Banda
        (-4.0, 107.5, "Lainnya"),                  # Laut Jawa utara, di luar semua kotak
    ],
)
def test_titik_kota_dan_laut(lintang, bujur, wilayah):
    assert tentukan_wilayah(lintang, bujur) == wilayah


def test_tepi_kotak_inklusif():
    assert tentukan_wilayah(-5.5, 105.0) == "Jawa"


def test_tumpang_tindih_bali_nusa_tenggara_vs_jawa():
    # Bujur 114,5 ada di kotak Jawa dan Bali & NT; Jawa menang karena diperiksa lebih dulu.
    assert tentukan_wilayah(-8.0, 114.5) == "Jawa"
