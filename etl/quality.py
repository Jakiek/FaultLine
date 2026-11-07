"""Aturan kualitas data Q1–Q5 (ARCHITECTURE § 7.4). Fungsi murni."""

from dataclasses import dataclass

from etl.config import BBOX, KEDALAMAN_MAKS_KM, KEDALAMAN_MIN_KM, TIPE_DITERIMA


@dataclass(frozen=True)
class Penolakan:
    event_id: str | None
    kode: str          # 'Q1' … 'Q5'
    keterangan: str
    payload: dict

    @property
    def alasan(self) -> str:
        """Teks untuk kolom etl_ditolak.alasan, selalu diawali kode aturan."""
        return f"{self.kode}: {self.keterangan}"


def _tolak(fitur: dict, kode: str, keterangan: str) -> Penolakan:
    return Penolakan(fitur.get("id"), kode, keterangan, fitur)


def periksa_fitur(fitur: dict) -> Penolakan | None:
    """Periksa satu fitur GeoJSON terhadap Q1–Q4. None berarti lolos."""
    props = fitur.get("properties") or {}
    koordinat = (fitur.get("geometry") or {}).get("coordinates") or []

    # Q1 — field wajib kosong. id/time/updated ikut diperiksa di sini agar
    # baris rusak tercatat, bukan membuat run gagal.
    if props.get("mag") is None:
        return _tolak(fitur, "Q1", "magnitudo kosong")
    if len(koordinat) < 3 or any(k is None for k in koordinat[:3]):
        return _tolak(fitur, "Q1", "koordinat atau kedalaman kosong")
    for nama in ("time", "updated"):
        if props.get(nama) is None:
            return _tolak(fitur, "Q1", f"properti '{nama}' kosong")
    if not fitur.get("id"):
        return _tolak(fitur, "Q1", "id event kosong")

    # Q2 — hanya gempa tektonik/vulkanik; ledakan tambang dsb. ditolak.
    tipe = props.get("type")
    if tipe != TIPE_DITERIMA:
        return _tolak(fitur, "Q2", f"type '{tipe}' bukan '{TIPE_DITERIMA}'")

    # GeoJSON: [bujur, lintang, kedalaman] — bujur lebih dulu.
    bujur, lintang, kedalaman = (float(k) for k in koordinat[:3])

    # Q3 — kedalaman di luar rentang wajar.
    if not KEDALAMAN_MIN_KM <= kedalaman <= KEDALAMAN_MAKS_KM:
        return _tolak(fitur, "Q3", f"kedalaman {kedalaman} km di luar {KEDALAMAN_MIN_KM}…{KEDALAMAN_MAKS_KM}")

    # Q4 — di luar kotak Indonesia (bisa terjadi saat transform diulang dari staging).
    if not (BBOX["minlongitude"] <= bujur <= BBOX["maxlongitude"]
            and BBOX["minlatitude"] <= lintang <= BBOX["maxlatitude"]):
        return _tolak(fitur, "Q4", f"koordinat ({lintang}, {bujur}) di luar kotak Indonesia")

    return None


def pilih_terbaru(fitur: list[dict]) -> tuple[list[dict], list[Penolakan]]:
    """Q5 — event_id yang muncul lebih dari sekali dalam batch.

    Simpan versi dengan properti 'updated' terbaru; bila sama, versi yang muncul
    terakhir. Versi lain dicatat sebagai penolakan Q5, tidak dibuang diam-diam.
    Fitur tanpa id dibiarkan lewat agar ditolak Q1 oleh periksa_fitur.
    """
    terpilih: dict[str, dict] = {}
    tanpa_id: list[dict] = []
    tersisih: list[Penolakan] = []

    for f in fitur:
        event_id = f.get("id")
        if not event_id:
            tanpa_id.append(f)
            continue
        lama = terpilih.get(event_id)
        if lama is None:
            terpilih[event_id] = f
            continue
        if _updated(f) >= _updated(lama):
            terpilih[event_id], kalah = f, lama
        else:
            kalah = f
        tersisih.append(_tolak(kalah, "Q5", "duplikat dalam batch; versi 'updated' terbaru disimpan"))

    return list(terpilih.values()) + tanpa_id, tersisih


def _updated(fitur: dict) -> int:
    return (fitur.get("properties") or {}).get("updated") or 0
