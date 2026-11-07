"""Satu-satunya modul yang menulis ke database."""

import logging
import os
from datetime import date
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from etl.quality import Penolakan
from etl.transform import BarisGempa

log = logging.getLogger(__name__)


def buka_koneksi(url: str | None = None) -> psycopg.Connection:
    """Buka koneksi dari argumen atau variabel lingkungan DATABASE_URL."""
    url = url or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL belum diatur (lihat .env.example).")
    # autocommit: setiap perubahan dibungkus eksplisit dengan conn.transaction().
    return psycopg.connect(url, autocommit=True)


# --- Migrasi ---

def jalankan_migrasi(conn: psycopg.Connection, folder: Path) -> list[str]:
    """Jalankan file sql/NNN_*.sql yang belum pernah dijalankan, berurutan.

    Nama file yang sudah dijalankan dicatat di skema_migrasi, sehingga
    `--mode init` aman diulang. Setiap file berjalan dalam transaksinya sendiri.
    """
    with conn.transaction():
        conn.execute(
            "CREATE TABLE IF NOT EXISTS skema_migrasi ("
            " nama TEXT PRIMARY KEY,"
            " dijalankan_pada TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        sudah = {r[0] for r in conn.execute("SELECT nama FROM skema_migrasi")}

    dijalankan = []
    for berkas in sorted(folder.glob("[0-9][0-9][0-9]_*.sql")):
        if berkas.name in sudah:
            continue
        with conn.transaction():
            conn.execute(berkas.read_text(encoding="utf-8"))
            conn.execute("INSERT INTO skema_migrasi (nama) VALUES (%s)", (berkas.name,))
        log.info("Migrasi %s dijalankan", berkas.name)
        dijalankan.append(berkas.name)
    return dijalankan


# --- Log ETL ---

def mulai_log(conn: psycopg.Connection, mode: str, awal: date, akhir: date) -> int:
    """Catat run baru berstatus 'berjalan' dan langsung commit agar terlihat."""
    with conn.transaction():
        run_id = conn.execute(
            "INSERT INTO etl_log (mode, rentang_awal, rentang_akhir)"
            " VALUES (%s, %s, %s) RETURNING run_id",
            (mode, awal, akhir),
        ).fetchone()[0]
    return run_id


def tambah_hitungan(
    conn: psycopg.Connection, run_id: int, diambil: int, insert: int, update: int, ditolak: int
) -> None:
    """Tambahkan hitungan satu jendela ke etl_log (dipanggil di dalam transaksi jendela)."""
    conn.execute(
        "UPDATE etl_log SET"
        " jumlah_diambil = jumlah_diambil + %s,"
        " jumlah_insert = jumlah_insert + %s,"
        " jumlah_update = jumlah_update + %s,"
        " jumlah_ditolak = jumlah_ditolak + %s"
        " WHERE run_id = %s",
        (diambil, insert, update, ditolak, run_id),
    )


def selesai_log(conn: psycopg.Connection, run_id: int, status: str, pesan: str | None = None) -> None:
    with conn.transaction():
        conn.execute(
            "UPDATE etl_log SET status = %s, pesan = %s, selesai = now() WHERE run_id = %s",
            (status, pesan, run_id),
        )


# --- Staging, fakta, penolakan ---

def simpan_mentah(conn: psycopg.Connection, run_id: int, fitur: list[dict]) -> None:
    """Simpan fitur mentah ke staging. Fitur tanpa id tetap tercatat di etl_ditolak (Q1)."""
    data = [(f["id"], Jsonb(f), run_id) for f in fitur if f.get("id")]
    if not data:
        return
    with conn.cursor() as cur:
        # Event tepat di batas dua jendela bisa terambil dua kali dalam satu run.
        cur.executemany(
            "INSERT INTO stg_gempa_mentah (event_id, payload, run_id) VALUES (%s, %s, %s)"
            " ON CONFLICT (event_id, run_id) DO NOTHING",
            data,
        )


_SQL_UPSERT = """
INSERT INTO fakta_gempa (
  event_id, tanggal_id, wilayah_id, waktu_utc, magnitudo, tipe_magnitudo,
  kelas_magnitudo, kedalaman_km, kelas_kedalaman, lintang, bujur, tempat,
  di_indonesia, signifikansi, tsunami, status, diperbarui_pada
)
VALUES (
  %(event_id)s, %(tanggal_id)s,
  (SELECT wilayah_id FROM dim_wilayah WHERE nama = %(wilayah)s),
  %(waktu_utc)s, %(magnitudo)s, %(tipe_magnitudo)s, %(kelas_magnitudo)s,
  %(kedalaman_km)s, %(kelas_kedalaman)s, %(lintang)s, %(bujur)s, %(tempat)s,
  %(di_indonesia)s, %(signifikansi)s, %(tsunami)s, %(status)s, %(diperbarui_pada)s
)
ON CONFLICT (event_id) DO UPDATE SET
  tanggal_id      = EXCLUDED.tanggal_id,
  wilayah_id      = EXCLUDED.wilayah_id,
  waktu_utc       = EXCLUDED.waktu_utc,
  magnitudo       = EXCLUDED.magnitudo,
  tipe_magnitudo  = EXCLUDED.tipe_magnitudo,
  kelas_magnitudo = EXCLUDED.kelas_magnitudo,
  kedalaman_km    = EXCLUDED.kedalaman_km,
  kelas_kedalaman = EXCLUDED.kelas_kedalaman,
  lintang         = EXCLUDED.lintang,
  bujur           = EXCLUDED.bujur,
  tempat          = EXCLUDED.tempat,
  di_indonesia    = EXCLUDED.di_indonesia,
  signifikansi    = EXCLUDED.signifikansi,
  tsunami         = EXCLUDED.tsunami,
  status          = EXCLUDED.status,
  diperbarui_pada = EXCLUDED.diperbarui_pada,
  dimuat_pada     = now()
WHERE fakta_gempa.diperbarui_pada < EXCLUDED.diperbarui_pada
RETURNING (xmax = 0) AS baru
"""


def upsert_fakta(conn: psycopg.Connection, baris: list[BarisGempa]) -> tuple[int, int]:
    """Upsert ke fakta_gempa. Mengembalikan (jumlah_insert, jumlah_update).

    Baris yang tidak lebih baru dari data tersimpan tidak mengembalikan apa pun
    (klausa WHERE), sehingga tidak dihitung sebagai insert maupun update.
    """
    if not baris:
        return 0, 0
    insert = update = 0
    with conn.cursor() as cur:
        cur.executemany(_SQL_UPSERT, [b.sebagai_dict() for b in baris], returning=True)
        while True:
            hasil = cur.fetchone()
            if hasil is not None:
                if hasil[0]:
                    insert += 1
                else:
                    update += 1
            if not cur.nextset():
                break
    return insert, update


def simpan_ditolak(conn: psycopg.Connection, run_id: int, penolakan: list[Penolakan]) -> None:
    if not penolakan:
        return
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO etl_ditolak (run_id, event_id, alasan, payload) VALUES (%s, %s, %s, %s)",
            [(run_id, p.event_id, p.alasan, Jsonb(p.payload)) for p in penolakan],
        )
