"""Filesystem locations used by NEXUS.

Windows data lives under ``%LOCALAPPDATA%\\Nexus``. macOS data uses the
conventional Library Application Support, Logs, and Caches locations. Paths may
be overridden for isolated tests with ``NEXUS_DATA_DIR`` and related variables.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "Nexus"
MAC_APP_DIR_NAME = "NEXUS"


def app_data_dir() -> Path:
    """Return the writable application data directory, creating it if needed."""
    override = os.environ.get("NEXUS_DATA_DIR")
    if override:
        base = Path(override)
    elif sys.platform == "win32":
        root = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        base = Path(root or Path.home()) / APP_DIR_NAME
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / MAC_APP_DIR_NAME
    else:
        base = Path.home() / f".{APP_DIR_NAME.lower()}"
    base.mkdir(parents=True, exist_ok=True)
    return base


def logs_dir() -> Path:
    override = os.environ.get("NEXUS_DATA_DIR")
    if override:
        path = Path(override) / "logs"
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Logs" / MAC_APP_DIR_NAME
    else:
        path = app_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_dir() -> Path:
    """Return a disposable cache location, separate from durable user data."""
    override = os.environ.get("NEXUS_CACHE_DIR")
    if override:
        path = Path(override)
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Caches" / MAC_APP_DIR_NAME
    else:
        path = app_data_dir() / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_path() -> Path:
    override = os.environ.get("NEXUS_DB_PATH")
    if override:
        p = Path(override)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    return app_data_dir() / "nexus_history.db"


def settings_path() -> Path:
    override = os.environ.get("NEXUS_SETTINGS_PATH")
    if override:
        p = Path(override)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    return app_data_dir() / "settings.json"


def default_export_dir() -> Path:
    path = app_data_dir() / "exports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def project_root() -> Path:
    """Directory containing the ``nexus`` package (source checkout or bundle)."""
    if getattr(sys, "frozen", False):  # PyInstaller
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent.parent


def assets_dir() -> Path:
    return project_root() / "assets"
