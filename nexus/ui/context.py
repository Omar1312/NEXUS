"""Shared dependency container passed to every page."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from nexus.core.gaming_session import GamingSessionRecorder
from nexus.database.repository import HistoryRepository
from nexus.services.history_service import HistoryRecorder
from nexus.services.monitoring_service import MonitoringService
from nexus.services.process_service import ProcessService
from nexus.services.settings_service import SettingsService


@dataclass
class AppContext:
    settings: SettingsService
    monitoring: MonitoringService
    processes: ProcessService
    repository: HistoryRepository
    history: HistoryRecorder
    gaming: GamingSessionRecorder
    database_persistent: bool = True
    theme_name: str = "dark"
    install_update: Callable[[Path], bool] | None = None
