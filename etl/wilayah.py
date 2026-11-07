"""Penentuan wilayah dengan pendekatan kotak batas (bukan batas administratif)."""

from etl.config import KOTAK_WILAYAH, WILAYAH_LAINNYA


def tentukan_wilayah(lintang: float, bujur: float) -> str:
    """Kembalikan nama wilayah pertama yang kotaknya memuat titik.

    Kotak saling tumpang tindih, jadi urutan di config menentukan hasil:
    Selat Sunda (105,5; −6) masuk Jawa karena Jawa diperiksa sebelum Sumatra.
    """
    for nama, bujur_min, bujur_maks, lintang_min, lintang_maks in KOTAK_WILAYAH:
        if bujur_min <= bujur <= bujur_maks and lintang_min <= lintang <= lintang_maks:
            return nama
    return WILAYAH_LAINNYA
