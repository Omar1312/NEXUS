"""Validated, persisted application settings.

Settings are stored as JSON in ``%LOCALAPPDATA%\\Nexus\\settings.json``. The
dataclass is deliberately Qt-free so it can be unit-tested in isolation; the
service wrapper adds change notifications and atomic saving.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal

from nexus.utils.exceptions import SettingsValidationError
from nexus.utils.paths import default_export_dir, settings_path

log = logging.getLogger(__name__)

THEMES = ("dark", "light", "system")
REFRESH_INTERVALS = (1, 2, 5)
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


@dataclass
class Settings:
    """All user-configurable preferences."""

    theme: str = "dark"
    refresh_interval_s: int = 2
    chart_history_points: int = 180
    cpu_warning_threshold: float = 85.0
    memory_warning_threshold: float = 85.0
    storage_warning_threshold: float = 10.0
    retention_days: int = 14
    start_minimized: bool = False
    launch_at_startup: bool = False
    export_dir: str = ""
    log_level: str = "INFO"
    store_history: bool = True
    gaming_report_dir: str = ""
    auto_update_checks: bool = False
    include_prereleases: bool = False
    last_update_check: str = ""

    def __post_init__(self) -> None:
        if not self.export_dir:
            self.export_dir = str(default_export_dir())
        if not self.gaming_report_dir:
            self.gaming_report_dir = str(default_export_dir())

    # -- validation ---------------------------------------------------------
    def validate(self) -> None:
        if self.theme not in THEMES:
            raise SettingsValidationError(f"Unknown theme: {self.theme!r}")
        if self.refresh_interval_s not in REFRESH_INTERVALS:
            raise SettingsValidationError(
                f"Refresh interval must be one of {REFRESH_INTERVALS} seconds."
            )
        if not 30 <= int(self.chart_history_points) <= 3600:
            raise SettingsValidationError("Chart history must be between 30 and 3600 points.")
        for name in ("cpu_warning_threshold", "memory_warning_threshold"):
            value = getattr(self, name)
            if not 30 <= float(value) <= 100:
                raise SettingsValidationError(f"{name} must be between 30 and 100 percent.")
        if not 1 <= float(self.storage_warning_threshold) <= 50:
            raise SettingsValidationError("Storage warning threshold must be between 1 and 50%.")
        if not 1 <= int(self.retention_days) <= 365:
            raise SettingsValidationError("Retention must be between 1 and 365 days.")
        if self.log_level not in LOG_LEVELS:
            raise SettingsValidationError(f"Unknown log level: {self.log_level!r}")
        if (
            not isinstance(self.auto_update_checks, bool)
            or not isinstance(self.include_prereleases, bool)
            or not isinstance(self.last_update_check, str)
        ):
            raise SettingsValidationError("Update preferences are invalid.")
        for path in (self.export_dir, self.gaming_report_dir):
            if not path:
                raise SettingsValidationError("Export directory cannot be empty.")
        if not isinstance(self.start_minimized, bool) or not isinstance(
            self.launch_at_startup, bool
        ):
            raise SettingsValidationError("Boolean preferences must be true or false.")

    # -- serialisation ------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Settings:
        """Build settings from JSON, ignoring unknown keys written by newer builds."""
        if not isinstance(data, dict):
            raise SettingsValidationError("Settings file must contain a JSON object.")
        allowed = {f.name for f in fields(cls)}
        types = {f.name: f.type for f in fields(cls)}
        clean: dict[str, Any] = {}
        for key, value in data.items():
            if key not in allowed:
                continue
            expected = types[key]
            try:
                if expected is bool or expected == "bool":
                    clean[key] = bool(value)
                elif expected is int or expected == "int":
                    clean[key] = int(value)
                elif expected is float or expected == "float":
                    clean[key] = float(value)
                else:
                    clean[key] = str(value)
            except (TypeError, ValueError) as exc:
                raise SettingsValidationError(f"Invalid value for {key}: {value!r}") from exc
        settings = cls(**clean)
        settings.validate()
        return settings


class SettingsService(QObject):
    """Loads, validates and saves settings atomically."""

    changed = Signal(object)  # Settings

    def __init__(self, path: Path | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._path = path or settings_path()
        self._settings = Settings()
        self._load()

    @property
    def path(self) -> Path:
        return self._path

    @property
    def current(self) -> Settings:
        return self._settings

    def _load(self) -> None:
        if not self._path.exists():
            self._save()
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            self._settings = Settings.from_dict(raw)
        except (OSError, json.JSONDecodeError, SettingsValidationError) as exc:
            log.warning("Invalid settings file (%s); restoring defaults.", exc)
            backup = self._path.with_suffix(".json.invalid")
            try:
                self._path.replace(backup)
            except OSError:
                pass
            self._settings = Settings()
            self._save()

    def _save(self) -> None:
        self._settings.validate()
        payload = json.dumps(self._settings.to_dict(), indent=2)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        handle, temp_name = tempfile.mkstemp(
            prefix="settings-", suffix=".tmp", dir=str(self._path.parent)
        )
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                stream.write(payload)
            os.replace(temp_name, self._path)
        except OSError as exc:
            log.error("Could not save settings to %s: %s", self._path, exc)
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise SettingsValidationError(
                "Settings could not be saved. Check folder permissions.",
                user_message="NEXUS could not save your settings.",
            ) from exc

    def update(self, **changes: Any) -> Settings:
        """Apply changes, validate, persist, and notify listeners."""
        candidate = Settings(**{**self._settings.to_dict(), **changes})
        candidate.validate()
        self._settings = candidate
        self._save()
        self.changed.emit(candidate)
        return candidate

    def save(self) -> None:
        self._save()
        self.changed.emit(self._settings)
