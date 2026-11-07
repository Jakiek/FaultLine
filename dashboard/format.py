"""Format angka dan waktu gaya Indonesia untuk tampilan dashboard."""

from datetime import datetime
from zoneinfo import ZoneInfo

WIB = ZoneInfo("Asia/Jakarta")


def angka(n: int | float) -> str:
    """1234567 → '1.234.567'."""
    return f"{round(n):,}".replace(",", ".")


def desimal(x: float, digit: int = 1) -> str:
    """5.65 → '5,7' (digit=1)."""
    return f"{x:,.{digit}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def waktu_wib(t: datetime) -> str:
    """datetime ber-zona waktu → '01-01-2024 07:59 WIB'."""
    return t.astimezone(WIB).strftime("%d-%m-%Y %H:%M") + " WIB"
