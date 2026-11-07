"""CLI pipeline: python -m etl.run --mode init|backfill|inkremental."""

import argparse
import logging
from datetime import UTC, date, datetime, timedelta

from dotenv import load_dotenv

from etl import extract, load, transform
from etl.config import FOLDER_SQL, JENDELA_INKREMENTAL_HARI, TANGGAL_MAKS, TANGGAL_MIN

log = logging.getLogger("etl")


def hari_ini_utc() -> date:
    return datetime.now(UTC).date()


def jendela_bulanan(mulai: date, akhir: date) -> list[tuple[date, date]]:
    """Pecah [mulai, akhir] (inklusif) menjadi jendela [awal, selesai) per bulan kalender."""
    jendela = []
    awal = mulai
    batas = akhir + timedelta(days=1)
    while awal < batas:
        bulan_depan = date(awal.year + awal.month // 12, awal.month % 12 + 1, 1)
        selesai = min(bulan_depan, batas)
        jendela.append((awal, selesai))
        awal = selesai
    return jendela


def proses_jendela(conn, run_id: int, mulai: date, selesai: date) -> tuple[int, int, int, int]:
    """Extract → staging → transform → load untuk satu jendela, dalam satu transaksi.

    Commit per jendela: bila bulan ke-90 gagal, 89 bulan sebelumnya tetap tersimpan.
    """
    fitur = extract.ambil_jendela(mulai, selesai)
    baris, ditolak = transform.ubah_batch(fitur)
    with conn.transaction():
        load.simpan_mentah(conn, run_id, fitur)
        insert, update = load.upsert_fakta(conn, baris)
        load.simpan_ditolak(conn, run_id, ditolak)
        load.tambah_hitungan(conn, run_id, len(fitur), insert, update, len(ditolak))
    log.info(
        "%s…%s: diambil %d, insert %d, update %d, tetap %d, ditolak %d",
        mulai, selesai, len(fitur), insert, update, len(baris) - insert - update, len(ditolak),
    )
    return len(fitur), insert, update, len(ditolak)


def jalankan_etl(mode: str, mulai: date, akhir: date) -> int:
    if mulai < TANGGAL_MIN or akhir > TANGGAL_MAKS or mulai > akhir:
        raise SystemExit(f"Rentang harus di dalam {TANGGAL_MIN}…{TANGGAL_MAKS} dan mulai ≤ akhir.")

    jendela = jendela_bulanan(mulai, akhir) if mode == "backfill" else [(mulai, akhir + timedelta(days=1))]
    with load.buka_koneksi() as conn:
        run_id = load.mulai_log(conn, mode, mulai, akhir)
        log.info("Run %d (%s) %s…%s, %d jendela", run_id, mode, mulai, akhir, len(jendela))
        total = [0, 0, 0, 0]
        try:
            for awal, selesai in jendela:
                for i, n in enumerate(proses_jendela(conn, run_id, awal, selesai)):
                    total[i] += n
        except BaseException as e:
            load.selesai_log(conn, run_id, "gagal", f"{type(e).__name__}: {e}"[:1000])
            log.exception("Run %d gagal", run_id)
            raise
        load.selesai_log(conn, run_id, "sukses")
    log.info(
        "Run %d sukses: diambil %d, insert %d, update %d, ditolak %d", run_id, *total
    )
    return run_id


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Pipeline ETL gempa Indonesia (USGS → PostgreSQL)")
    parser.add_argument("--mode", required=True, choices=["init", "backfill", "inkremental"])
    parser.add_argument("--mulai", type=date.fromisoformat, help="backfill: tanggal awal UTC (YYYY-MM-DD)")
    parser.add_argument("--akhir", type=date.fromisoformat, help="backfill: tanggal akhir UTC, default hari ini")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    load_dotenv()

    if args.mode == "init":
        with load.buka_koneksi() as conn:
            baru = load.jalankan_migrasi(conn, FOLDER_SQL)
        log.info("Init selesai; migrasi baru: %s", ", ".join(baru) or "tidak ada")
        return

    hari_ini = hari_ini_utc()
    if args.mode == "backfill":
        if args.mulai is None:
            parser.error("--mode backfill membutuhkan --mulai")
        jalankan_etl("backfill", args.mulai, args.akhir or hari_ini)
    else:
        # 30 hari terakhir: menangkap event baru sekaligus revisi event lama.
        jalankan_etl("inkremental", hari_ini - timedelta(days=JENDELA_INKREMENTAL_HARI), hari_ini)


if __name__ == "__main__":
    main()
