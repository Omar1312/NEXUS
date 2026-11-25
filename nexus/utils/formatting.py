"""Human-readable formatting for metric values.

All functions are pure and unit-tested. Binary units (KiB/MiB/GiB) are used for
storage sizes; network throughput is shown in both bytes/s and bits/s because
Windows and ISPs commonly report the latter.
"""

from __future__ import annotations

from datetime import datetime

_BYTE_UNITS = ("B", "KiB", "MiB", "GiB", "TiB", "PiB")
_BIT_UNITS = ("bit/s", "Kbit/s", "Mbit/s", "Gbit/s", "Tbit/s")

UNAVAILABLE = "Unavailable"


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def format_bytes(value: float | None, *, precision: int = 1) -> str:
    """Format a byte count using binary prefixes, e.g. ``15.8 GiB``."""
    if value is None:
        return UNAVAILABLE
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return UNAVAILABLE
    if amount < 0:
        return UNAVAILABLE
    if amount == 0:
        return "0 B"
    index = 0
    while amount >= 1024 and index < len(_BYTE_UNITS) - 1:
        amount /= 1024.0
        index += 1
    digits = 0 if index == 0 or amount >= 100 else precision
    return f"{amount:.{digits}f} {_BYTE_UNITS[index]}"


def format_rate(bytes_per_second: float | None, *, precision: int = 1) -> str:
    """Format a byte throughput, e.g. ``12.4 MB/s``."""
    if bytes_per_second is None:
        return UNAVAILABLE
    if bytes_per_second < 0:
        return UNAVAILABLE
    formatted = format_bytes(bytes_per_second, precision=precision)
    if formatted == "0 B":
        return "0 B/s"
    return f"{formatted}/s"


def format_bitrate(bytes_per_second: float | None, *, precision: int = 1) -> str:
    """Format a byte throughput as a bit rate, e.g. ``99.2 Mbit/s``."""
    if bytes_per_second is None or bytes_per_second < 0:
        return UNAVAILABLE
    bits = float(bytes_per_second) * 8.0
    if bits == 0:
        return "0 bit/s"
    index = 0
    while bits >= 1000 and index < len(_BIT_UNITS) - 1:
        bits /= 1000.0
        index += 1
    digits = 0 if index == 0 or bits >= 100 else precision
    return f"{bits:.{digits}f} {_BIT_UNITS[index]}"


def format_percent(value: float | None, *, precision: int = 0) -> str:
    if value is None:
        return UNAVAILABLE
    return f"{clamp(value, 0.0, 100.0):.{precision}f}%"


def format_frequency(mhz: float | None) -> str:
    """Format a CPU/GPU clock given in MHz."""
    if mhz is None or mhz <= 0:
        return UNAVAILABLE
    if mhz >= 1000:
        return f"{mhz / 1000.0:.2f} GHz"
    return f"{mhz:.0f} MHz"


def format_temperature(celsius: float | None) -> str:
    if celsius is None:
        return UNAVAILABLE
    return f"{celsius:.0f} °C"


def format_power(watts: float | None) -> str:
    if watts is None:
        return UNAVAILABLE
    return f"{watts:.1f} W"


def format_duration(total_seconds: float | None) -> str:
    """Format a duration as ``3d 04h``, ``2h 07m`` or ``42s``."""
    if total_seconds is None or total_seconds < 0:
        return UNAVAILABLE
    seconds = int(total_seconds)
    days, rem = divmod(seconds, 86_400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    if days:
        return f"{days}d {hours:02d}h"
    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def format_timestamp(epoch: float) -> str:
    return datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M:%S")


def format_time_short(epoch: float) -> str:
    return datetime.fromtimestamp(epoch).strftime("%H:%M:%S")


def format_relative(epoch: float, *, now: float) -> str:
    delta = max(0, int(now - epoch))
    if delta < 2:
        return "just now"
    if delta < 60:
        return f"{delta}s ago"
    if delta < 3600:
        return f"{delta // 60}m ago"
    return f"{delta // 3600}h ago"


def format_count(value: int | None) -> str:
    if value is None:
        return UNAVAILABLE
    return f"{value:,}"
