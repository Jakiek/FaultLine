"""Transform fitur GeoJSON USGS menjadi baris fakta. Fungsi murni: tanpa jaringan, tanpa DB."""

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from etl.config import BATAS_DALAM_KM, BATAS_DANGKAL_KM, KELAS_MAGNITUDO
from etl.quality import Penolakan, periksa_fitur, pilih_terbaru
from etl.wilayah import tentukan_wilayah

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


@dataclass(frozen=True)
class BarisGempa:
    event_id: str
    tanggal_id: int
    wilayah: str
    waktu_utc: datetime
    magnitudo: Decimal
    tipe_magnitudo: str | None
    kelas_magnitudo: str
    kedalaman_km: Decimal
    kelas_kedalaman: str
    lintang: Decimal
    bujur: Decimal
    tempat: str | None
    di_indonesia: bool
    signifikansi: int | None
    tsunami: bool
    status: str
    diperbarui_pada: datetime

    def sebagai_dict(self) -> dict:
        return asdict(self)


def ms_ke_utc(ms: int) -> datetime:
    """Milidetik epoch USGS → datetime UTC (tanpa pembulatan float)."""
    return _EPOCH + timedelta(milliseconds=ms)


def bulatkan(nilai: float, desimal: int) -> Decimal:
    """Bulatkan setengah ke atas seperti NUMERIC PostgreSQL, bukan banker's rounding."""
    return Decimal(str(nilai)).quantize(Decimal(1).scaleb(-desimal), rounding=ROUND_HALF_UP)


def kelas_kedalaman(kedalaman_km: Decimal | float) -> str:
    if kedalaman_km < BATAS_DANGKAL_KM:
        return "dangkal"
    if kedalaman_km <= BATAS_DALAM_KM:
        return "menengah"
    return "dalam"


def kelas_magnitudo(magnitudo: Decimal | float) -> str:
    for ambang, nama in KELAS_MAGNITUDO:
        if magnitudo >= ambang:
            return nama
    # Query USGS memakai minmagnitude, jadi nilai di bawah ambang tidak masuk pipeline.
    raise ValueError(f"magnitudo {magnitudo} di bawah ambang pipeline")


def ubah_fitur(fitur: dict) -> BarisGempa | Penolakan:
    """Satu fitur GeoJSON → BarisGempa, atau Penolakan bila melanggar Q1–Q4."""
    penolakan = periksa_fitur(fitur)
    if penolakan is not None:
        return penolakan

    props = fitur["properties"]
    bujur, lintang, kedalaman = fitur["geometry"]["coordinates"][:3]

    # Dibulatkan dulu ke presisi kolom, lalu diklasifikasi, agar kelas selalu
    # sesuai dengan angka yang tersimpan (mis. 4,95 tersimpan 5,0 → 'sedang').
    magnitudo = bulatkan(props["mag"], 1)
    kedalaman_km = bulatkan(kedalaman, 2)
    lintang_d = bulatkan(lintang, 4)
    bujur_d = bulatkan(bujur, 4)
    waktu = ms_ke_utc(props["time"])
    tempat = props.get("place")

    return BarisGempa(
        event_id=fitur["id"],
        tanggal_id=int(waktu.strftime("%Y%m%d")),   # dari tanggal UTC
        wilayah=tentukan_wilayah(float(lintang_d), float(bujur_d)),
        waktu_utc=waktu,
        magnitudo=magnitudo,
        tipe_magnitudo=props.get("magType"),
        kelas_magnitudo=kelas_magnitudo(magnitudo),
        kedalaman_km=kedalaman_km,
        kelas_kedalaman=kelas_kedalaman(kedalaman_km),
        lintang=lintang_d,
        bujur=bujur_d,
        tempat=tempat,
        di_indonesia=bool(tempat) and tempat.strip().endswith("Indonesia"),
        signifikansi=props.get("sig"),
        tsunami=bool(props.get("tsunami")),
        status=props.get("status") or "automatic",
        diperbarui_pada=ms_ke_utc(props["updated"]),
    )


def ubah_batch(fitur: list[dict]) -> tuple[list[BarisGempa], list[Penolakan]]:
    """Terapkan Q5 (duplikat) lalu Q1–Q4 pada satu batch fitur."""
    unik, ditolak = pilih_terbaru(fitur)
    baris: list[BarisGempa] = []
    for f in unik:
        hasil = ubah_fitur(f)
        if isinstance(hasil, Penolakan):
            ditolak.append(hasil)
        else:
            baris.append(hasil)
    return baris, ditolak
