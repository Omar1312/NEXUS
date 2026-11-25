"""Read-only Windows helpers (registry, OS identity, adapter enumeration).

Nothing here modifies the registry. All access is best-effort and returns
``None``/empty values rather than raising when a key or API is unavailable.
"""

from __future__ import annotations

import logging
import platform
import sys
from datetime import datetime
from typing import Any

from nexus.core.metrics import SystemInfo

log = logging.getLogger(__name__)

IS_WINDOWS = sys.platform == "win32"


def registry_value(root: int, path: str, name: str) -> Any | None:
    if not IS_WINDOWS:
        return None
    try:
        import winreg

        with winreg.OpenKey(root, path, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, name)
            return value
    except (OSError, ImportError, ValueError):
        return None


def cpu_brand() -> str:
    """Marketing name of the CPU, e.g. ``Intel(R) Core(TM) i7-14700HX``."""
    if IS_WINDOWS:
        import winreg

        name = registry_value(
            winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            "ProcessorNameString",
        )
        if isinstance(name, str) and name.strip():
            return " ".join(name.split())
    brand = platform.processor()
    return brand or "Unknown CPU"


def os_info() -> SystemInfo:
    build = ""
    display_version = ""
    if IS_WINDOWS:
        import winreg

        build_value = registry_value(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
            "CurrentBuildNumber",
        )
        display_version = str(
            registry_value(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
                "DisplayVersion",
            )
            or ""
        )
        build = str(build_value or "")

    product = platform.system() or "Windows"
    try:
        build_number = int(build) if build else 0
    except ValueError:
        build_number = 0
    if build_number >= 22000:
        name = "Windows 11"
    elif build_number >= 10240:
        name = "Windows 10"
    else:
        name = f"{product} {platform.release()}".strip()

    version = " ".join(part for part in (display_version, build) if part) or platform.version()
    return SystemInfo(
        hostname=platform.node(),
        os_name=name,
        os_version=version,
        os_build=build,
        architecture=platform.machine(),
    )


def uptime_seconds() -> float | None:
    try:
        import psutil

        return max(0.0, datetime.now().timestamp() - psutil.boot_time())
    except Exception as exc:  # pragma: no cover - defensive
        log.debug("Uptime unavailable: %s", exc)
        return None


def display_adapter_names() -> list[str]:
    """Enumerate physical display adapters using GDI (fast, no WMI)."""
    if not IS_WINDOWS:
        return []
    try:
        import win32api

        names: list[str] = []
        index = 0
        while True:
            try:
                device = win32api.EnumDisplayDevices(None, index, 0)
            except Exception:
                break
            if not device or not device.DeviceString:
                break
            name = str(device.DeviceString).strip()
            # Skip software/virtual display drivers that expose no sensors.
            if name and name not in names and "Virtual" not in name:
                names.append(name)
            index += 1
            if index > 16:
                break
        return names
    except Exception as exc:
        log.debug("Display adapter enumeration failed: %s", exc)
        return []


def is_elevated() -> bool:
    """Whether the current process has administrator rights (read-only check)."""
    if not IS_WINDOWS:
        return False
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
    except Exception:
        return False


def windows_build_number() -> int | None:
    if not IS_WINDOWS:
        return None
    import winreg

    raw = registry_value(
        winreg.HKEY_LOCAL_MACHINE,
        r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
        "CurrentBuildNumber",
    )
    try:
        return int(str(raw))
    except (TypeError, ValueError):
        return None
