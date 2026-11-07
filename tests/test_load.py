"""Test integrasi load ke PostgreSQL sungguhan.

Butuh TEST_DATABASE_URL yang menunjuk database khusus test; isinya dihapus
setiap test. Tanpa variabel itu, test di berkas ini dilewati.
"""

import os
from datetime import date

import pytest

from etl import load
from etl.config import FOLDER_SQL
from etl.transform import ubah_batch
from tests.conftest import buat_fitur

URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL belum diatur")


@pytest.fixture
def conn():
    with load.buka_koneksi(URL) as c:
        c.execute("DROP SCHEMA public CASCADE")
        c.execute("CREATE SCHEMA public")
        load.jalankan_migrasi(c, FOLDER_SQL)
        yield c


def _muat(conn, fitur: list[dict], run_id: int) -> tuple[int, int]:
    baris, ditolak = ubah_batch(fitur)
    with conn.transaction():
        load.simpan_mentah(conn, run_id, fitur)
        hasil = load.upsert_fakta(conn, baris)
        load.simpan_ditolak(conn, run_id, ditolak)
    return hasil


def _satu(conn, sql: str, params=()):
    return conn.execute(sql, params).fetchone()[0]


def test_migrasi_mengisi_dimensi(conn):
    assert _satu(conn, "SELECT COUNT(*) FROM dim_tanggal") == 5479
    assert _satu(conn, "SELECT COUNT(*) FROM dim_wilayah") == 8
    assert load.jalankan_migrasi(conn, FOLDER_SQL) == []   # init kedua tidak menjalankan apa pun


def test_run_kedua_tidak_menambah_baris(conn, fitur_usgs):
    fitur = fitur_usgs + [buat_fitur(event_id="a"), buat_fitur(event_id="b")]
    run1 = load.mulai_log(conn, "backfill", date(2024, 1, 1), date(2024, 1, 31))
    assert _muat(conn, fitur, run1) == (3, 0)

    run2 = load.mulai_log(conn, "backfill", date(2024, 1, 1), date(2024, 1, 31))
    assert _muat(conn, fitur, run2) == (0, 0)
    assert _satu(conn, "SELECT COUNT(*) FROM fakta_gempa") == 3
    # Staging menyimpan salinan per run; penolakan tercatat per run.
    assert _satu(conn, "SELECT COUNT(*) FROM stg_gempa_mentah") == 2 * len(fitur)
    assert _satu(conn, "SELECT COUNT(*) FROM etl_ditolak WHERE run_id = %s", (run2,)) == 2


def test_revisi_usgs_memperbarui_baris(conn):
    run = load.mulai_log(conn, "inkremental", date(2024, 1, 1), date(2024, 1, 31))
    _muat(conn, [buat_fitur(event_id="rev", mag=5.8, updated=1_000)], run)
    assert _muat(conn, [buat_fitur(event_id="rev", mag=6.1, updated=2_000)], run) == (0, 1)
    mag, kelas = conn.execute("SELECT magnitudo, kelas_magnitudo FROM fakta_gempa WHERE event_id='rev'").fetchone()
    assert (str(mag), kelas) == ("6.1", "kuat")


def test_data_lama_tidak_menimpa_data_baru(conn):
    run = load.mulai_log(conn, "inkremental", date(2024, 1, 1), date(2024, 1, 31))
    _muat(conn, [buat_fitur(event_id="rev", mag=6.1, updated=2_000)], run)
    assert _muat(conn, [buat_fitur(event_id="rev", mag=5.8, updated=1_000)], run) == (0, 0)
    assert str(_satu(conn, "SELECT magnitudo FROM fakta_gempa WHERE event_id='rev'")) == "6.1"


def test_hitungan_dan_status_log(conn):
    run = load.mulai_log(conn, "backfill", date(2024, 1, 1), date(2024, 1, 31))
    with conn.transaction():
        load.tambah_hitungan(conn, run, 10, 7, 1, 2)
        load.tambah_hitungan(conn, run, 5, 3, 0, 1)
    load.selesai_log(conn, run, "sukses")
    baris = conn.execute(
        "SELECT jumlah_diambil, jumlah_insert, jumlah_update, jumlah_ditolak, status, selesai IS NOT NULL"
        " FROM etl_log WHERE run_id = %s", (run,)
    ).fetchone()
    assert baris == (15, 10, 1, 3, "sukses", True)


def test_jendela_gagal_tidak_meninggalkan_baris_setengah(conn):
    run = load.mulai_log(conn, "backfill", date(2024, 1, 1), date(2024, 1, 31))
    baris, _ = ubah_batch([buat_fitur(event_id="x")])
    with pytest.raises(RuntimeError):
        with conn.transaction():
            load.upsert_fakta(conn, baris)
            raise RuntimeError("gagal di tengah jendela")
    assert _satu(conn, "SELECT COUNT(*) FROM fakta_gempa") == 0
