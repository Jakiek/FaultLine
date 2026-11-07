from datetime import date

from etl.run import jendela_bulanan


def test_jendela_bulanan_menutup_rentang_tanpa_celah():
    jendela = jendela_bulanan(date(2023, 11, 15), date(2024, 2, 3))
    assert jendela == [
        (date(2023, 11, 15), date(2023, 12, 1)),
        (date(2023, 12, 1), date(2024, 1, 1)),     # pergantian tahun
        (date(2024, 1, 1), date(2024, 2, 1)),
        (date(2024, 2, 1), date(2024, 2, 4)),      # hari terakhir ikut (akhir inklusif)
    ]


def test_jendela_satu_hari():
    assert jendela_bulanan(date(2024, 3, 31), date(2024, 3, 31)) == [(date(2024, 3, 31), date(2024, 4, 1))]
