"""Explicit, reversible registration of NEXUS in the per-user Run key.

This module is only ever called after the user ticks "Launch at Windows
startup" and confirms the operating-system change. Nothing is installed as a
service or scheduled task.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from nexus.utils.exceptions import UnsupportedPlatformError
from nexus.utils.paths import project_root

log = logging.getLogger(__name__)

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "Nexus"


def _winreg():
    try:
        import winreg  # type: ignore
    except ImportError as exc:  # pragma: no cover - Windows only
        raise UnsupportedPlatformError("winreg is only available on Windows.") from exc
    return winreg


def startup_command() -> str:
    """Return the command Windows should execute at sign-in."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    entry = project_root() / "main.py"
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    launcher = pythonw if pythonw.exists() else Path(sys.executable)
    return f'"{launcher}" "{entry}" --minimized'


def is_registered() -> bool:
    """True when the current command is present in HKCU Run."""
    winreg = _winreg()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, VALUE_NAME)
            return bool(value)
    except FileNotFoundError:
        return False
    except OSError as exc:
        log.debug("Could not read startup registration: %s", exc)
        return False


def register() -> None:
    """Add or refresh the HKCU Run entry (no admin rights required)."""
    winreg = _winreg()
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, startup_command())
    log.info("Registered NEXUS for current-user startup.")


def unregister() -> None:
    """Remove the HKCU Run entry. Safe when the value is absent."""
    winreg = _winreg()
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, VALUE_NAME)
    except FileNotFoundError:
        return
    except OSError as exc:
        log.warning("Could not remove startup registration: %s", exc)
        raise
    log.info("Removed NEXUS startup registration.")
