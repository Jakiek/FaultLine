import copy
import json
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv()

_FIXTURE = Path(__file__).parent / "fixtures" / "usgs_contoh.json"


@pytest.fixture
def fitur_usgs() -> list[dict]:
    """[0] gempa normal (Cianjur), [1] 'quarry blast' (disunting), [2] tanpa magnitudo (disunting)."""
    return copy.deepcopy(json.loads(_FIXTURE.read_text(encoding="utf-8"))["features"])


@pytest.fixture
def fitur_normal(fitur_usgs) -> dict:
    return fitur_usgs[0]


def buat_fitur(
    event_id: str = "uji0001",
    bujur: float = 110.0,
    lintang: float = -7.0,
    kedalaman: float = 10.0,
    mag: float | None = 5.0,
    time: int = 1_704_070_759_656,
    updated: int = 1_710_020_291_040,
    tipe: str = "earthquake",
) -> dict:
    """Fitur GeoJSON sintetis berbentuk sama dengan respons USGS."""
    return {
        "type": "Feature",
        "id": event_id,
        "geometry": {"type": "Point", "coordinates": [bujur, lintang, kedalaman]},
        "properties": {
            "mag": mag, "magType": "mb", "place": "uji, Indonesia", "time": time,
            "updated": updated, "tsunami": 0, "sig": 400, "status": "reviewed", "type": tipe,
        },
    }
