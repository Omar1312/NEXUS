"""Top-level window: sidebar, header controls and lazy page switching."""

from __future__ import annotations

import logging

from PySide6.QtCore import QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from nexus import __version__
from nexus.platforms.selection import platform_id
from nexus.ui import icons, theme
from nexus.ui.base import BasePage
from nexus.ui.context import AppContext
from nexus.ui.dashboard import DashboardPage
from nexus.ui.gaming_page import GamingPage
from nexus.ui.hardware_page import HardwarePage
from nexus.ui.history_page import HistoryPage
from nexus.ui.optimizer_page import OptimizerPage
from nexus.ui.processes_page import ProcessesPage
from nexus.ui.reports_page import ReportsPage
from nexus.ui.settings_page import SettingsPage
from nexus.ui.sidebar import NAV_ITEMS, Sidebar
from nexus.ui.startup_page import StartupPage
from nexus.ui.storage_page import StoragePage
from nexus.ui.widgets.common import StatusPill
from nexus.utils import formatting
from nexus.utils.paths import logs_dir

log = logging.getLogger(__name__)

PAGE_CLASSES: dict[str, type[BasePage]] = {
    "dashboard": DashboardPage,
    "hardware": HardwarePage,
    "processes": ProcessesPage,
    "optimizer": OptimizerPage,
    "startup": StartupPage,
    "storage": StoragePage,
    "gaming": GamingPage,
    "history": HistoryPage,
    "reports": ReportsPage,
    "settings": SettingsPage,
}

PAGE_META: dict[str, tuple[str, str]] = {
    "dashboard": ("Dashboard", "Live performance overview of this computer"),
    "hardware": ("Hardware Monitor", "Sensors, tracked session statistics and capability status"),
    "processes": ("Processes", "Inspect running applications and close them safely"),
    "optimizer": ("Optimization Center", "Measured diagnostics and explainable recommendations"),
    "startup": ("Startup Applications", "Review user login items and startup agents"),
    "storage": ("Storage Analyzer", "Understand what occupies disk space"),
    "gaming": ("Gaming Mode", "Record a session and review real resource behaviour"),
    "history": ("Performance History", "Locally stored time-series measurements"),
    "reports": ("Reports", "Preview and export a summary of measured data"),
    "settings": ("Settings", "Monitoring, thresholds, storage and appearance"),
}


class MainWindow(QMainWindow):
    def __init__(self, app: QApplication, context: AppContext) -> None:
        super().__init__()
        self._app = app
        self.context = context
        self._theme_mode = context.settings.current.theme
        self._resolved_theme = context.theme_name
        self._active_key: str | None = None
        self._pages: dict[str, BasePage] = {}
        self._toast: QLabel | None = None

        title = "NEXUS — System Monitor" if platform_id() == "macos" else "NEXUS — Windows Performance Monitor"
        self.setWindowTitle(title)
        self.setWindowIcon(icons.app_icon())
        self.setMinimumSize(1120, 720)

        root = QWidget()
        root.setObjectName("appRoot")
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.pageSelected.connect(self.navigate)
        root_layout.addWidget(self.sidebar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        root_layout.addWidget(content, 1)

        content_layout.addWidget(self._build_header())
        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFixedHeight(1)
        content_layout.addWidget(divider)

        self.stack = QStackedWidget()
        self.stack.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(self.stack, 1)

        self._create_pages()
        self.navigate("dashboard")

        self._header_timer = QTimer(self)
        self._header_timer.setInterval(1000)
        self._header_timer.timeout.connect(self._update_last_update)
        self._header_timer.start()

        self.context.monitoring.snapshotReady.connect(self._on_snapshot)
        self.context.monitoring.errorOccurred.connect(self._on_monitoring_error)
        self.context.monitoring.runningChanged.connect(self._on_running_changed)
        self.context.monitoring.capabilitiesReady.connect(lambda _caps: None)
        self.context.settings.changed.connect(self._on_settings_changed)
        self.context.history.errorOccurred.connect(
            lambda message: self.show_toast(message, "warning")
        )

        self._install_shortcuts()

    # -- construction -------------------------------------------------------
    def _build_header(self) -> QWidget:
        palette = theme.current_palette()
        header = QWidget()
        header.setFixedHeight(86)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(26, 15, 22, 12)
        layout.setSpacing(12)

        text_box = QVBoxLayout()
        text_box.setSpacing(1)
        self.title_label = QLabel("Dashboard")
        self.title_label.setObjectName("pageTitle")
        self.subtitle_label = QLabel("Live performance overview of this computer")
        self.subtitle_label.setObjectName("pageSubtitle")
        text_box.addWidget(self.title_label)
        text_box.addWidget(self.subtitle_label)
        layout.addLayout(text_box, 1)

        self.status_pill = StatusPill("Starting…")
        self.status_pill.set_state("Starting…", palette.warning)
        layout.addWidget(self.status_pill, 0, Qt.AlignmentFlag.AlignVCenter)

        self.updated_label = QLabel("Waiting for data")
        self.updated_label.setObjectName("muted")
        self.updated_label.setMinimumWidth(118)
        self.updated_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.updated_label, 0, Qt.AlignmentFlag.AlignVCenter)

        self.refresh_button = QToolButton()
        self.refresh_button.setIcon(icons.make_icon("refresh", palette.text_muted, 18, palette.text))
        self.refresh_button.setIconSize(QSize(18, 18))
        self.refresh_button.setToolTip("Refresh now (F5)")
        self.refresh_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_button.clicked.connect(self._manual_refresh)
        layout.addWidget(self.refresh_button)

        self.pause_button = QToolButton()
        self.pause_button.setIcon(icons.make_icon("pause", palette.text_muted, 18, palette.text))
        self.pause_button.setIconSize(QSize(18, 18))
        self.pause_button.setToolTip("Pause monitoring")
        self.pause_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pause_button.clicked.connect(self._toggle_monitoring)
        layout.addWidget(self.pause_button)

        self.theme_button = QToolButton()
        self.theme_button.setIcon(
            icons.make_icon(
                "sun" if self._resolved_theme == "dark" else "moon",
                palette.text_muted,
                18,
                palette.text,
            )
        )
        self.theme_button.setIconSize(QSize(18, 18))
        self.theme_button.setToolTip("Switch between dark and light theme")
        self.theme_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_button.clicked.connect(self._toggle_theme)
        layout.addWidget(self.theme_button)

        self.logs_button = QToolButton()
        self.logs_button.setIcon(icons.make_icon("folder", palette.text_muted, 18, palette.text))
        self.logs_button.setIconSize(QSize(18, 18))
        self.logs_button.setToolTip(f"Open log folder\n{logs_dir()}")
        self.logs_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.logs_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(logs_dir())))
        )
        layout.addWidget(self.logs_button)
        return header

    def _create_pages(self) -> None:
        for key, page_class in PAGE_CLASSES.items():
            page = page_class(self.context)
            page.navigateRequested.connect(self.navigate)
            self._pages[key] = page
            self.stack.addWidget(page)

    def _install_shortcuts(self) -> None:
        refresh_key = "Meta+R" if platform_id() == "macos" else "F5"
        QShortcut(QKeySequence(refresh_key), self, activated=self._manual_refresh)
        for index, (key, _label, _icon, shortcut) in enumerate(NAV_ITEMS):
            QShortcut(QKeySequence(shortcut), self, activated=lambda k=key: self.navigate(k))

    # -- navigation ---------------------------------------------------------
    def navigate(self, key: str) -> None:
        page = self._pages.get(key)
        if page is None or key == self._active_key:
            if page is not None and self.stack.currentWidget() is not page:
                self.stack.setCurrentWidget(page)
            return
        if self._active_key is not None:
            previous = self._pages.get(self._active_key)
            if previous is not None:
                try:
                    previous.on_deactivated()
                except Exception:
                    log.exception("Page %s deactivation failed", self._active_key)
        self._active_key = key
        self.stack.setCurrentWidget(page)
        self.sidebar.set_current(key)
        title, subtitle = PAGE_META.get(key, (page.title, page.subtitle))
        self.title_label.setText(title)
        self.subtitle_label.setText(subtitle)
        try:
            page.on_activated()
        except Exception:
            log.exception("Page %s activation failed", key)

    @property
    def active_page(self) -> BasePage | None:
        return self._pages.get(self._active_key) if self._active_key else None

    # -- header behaviour ---------------------------------------------------
    def _on_snapshot(self, snapshot) -> None:
        if self.context.monitoring.running:
            interval = self.context.monitoring.interval_s
            self.status_pill.set_state(f"Live · {interval}s", theme.current_palette().success)
        self._update_last_update()

    def _update_last_update(self) -> None:
        last = self.context.monitoring.last_update
        if last is None:
            self.updated_label.setText("Waiting for data")
            return
        import time

        self.updated_label.setText(f"Updated {formatting.format_time_short(last)}")
        self.updated_label.setToolTip(
            f"Last successful update {formatting.format_relative(last, now=time.time())}"
        )

    def _on_monitoring_error(self, message: str) -> None:
        palette = theme.current_palette()
        self.status_pill.set_state("Data error", palette.critical)
        self.status_pill.setToolTip(message)
        self.show_toast(message, "error")

    def _on_running_changed(self, running: bool) -> None:
        palette = theme.current_palette()
        if running:
            self.status_pill.set_state(
                f"Live · {self.context.monitoring.interval_s}s", palette.success
            )
            self.pause_button.setIcon(
                icons.make_icon("pause", palette.text_muted, 18, palette.text)
            )
            self.pause_button.setToolTip("Pause monitoring")
        else:
            self.status_pill.set_state("Paused", palette.warning)
            self.pause_button.setIcon(
                icons.make_icon("play", palette.text_muted, 18, palette.text)
            )
            self.pause_button.setToolTip("Resume monitoring")

    def _toggle_monitoring(self) -> None:
        if self.context.monitoring.running:
            self.context.monitoring.stop()
        else:
            self.context.monitoring.start()

    def _manual_refresh(self) -> None:
        self.context.monitoring.refresh_now()
        page = self.active_page
        if page is not None:
            page.refresh_now()

    def _toggle_theme(self) -> None:
        target = "light" if self._resolved_theme == "dark" else "dark"
        try:
            self.context.settings.update(theme=target)
        except Exception as exc:
            log.warning("Theme change failed: %s", exc)

    def _on_settings_changed(self, settings) -> None:
        if settings.theme != self._theme_mode:
            self._theme_mode = settings.theme
            self.apply_theme(settings.theme)
        if settings.refresh_interval_s != self.context.monitoring.interval_s:
            self.context.monitoring.set_interval(settings.refresh_interval_s)
            if self.context.monitoring.running:
                self.status_pill.set_state(
                    f"Live · {settings.refresh_interval_s}s", theme.current_palette().success
                )
        if self.context.monitoring.running:
            self.context.monitoring.set_log_level(settings.log_level)
        self.context.history.set_retention_days(settings.retention_days)
        self.context.history.set_enabled(settings.store_history)
        for page in self._pages.values():
            page.refresh_theme()

    def apply_theme(self, mode: str) -> None:
        resolved = theme.apply_theme(self._app, mode)
        self._resolved_theme = resolved
        self.context.theme_name = resolved
        self.sidebar.refresh_theme()
        palette = theme.current_palette()
        self.theme_button.setIcon(
            icons.make_icon(
                "sun" if resolved == "dark" else "moon", palette.text_muted, 18, palette.text
            )
        )
        for button, icon_name in (
            (self.refresh_button, "refresh"),
            (self.pause_button, "pause" if self.context.monitoring.running else "play"),
            (self.logs_button, "folder"),
        ):
            button.setIcon(icons.make_icon(icon_name, palette.text_muted, 18, palette.text))
        for page in self._pages.values():
            page.refresh_theme()

    # -- notifications ------------------------------------------------------
    def show_toast(self, message: str, level: str = "info") -> None:
        palette = theme.current_palette()
        color = {
            "info": palette.accent_hover,
            "success": palette.success,
            "warning": palette.warning,
            "error": palette.critical,
        }.get(level, palette.accent_hover)
        if self._toast is not None:
            self._toast.deleteLater()
        toast = QLabel(message, self)
        toast.setWordWrap(True)
        toast.setMaximumWidth(460)
        toast.setStyleSheet(
            f"background-color: {palette.card}; color: {palette.text};"
            f"border: 1px solid {color}; border-radius: 10px; padding: 10px 14px;"
            "font-size: 9pt;"
        )
        toast.adjustSize()
        toast.move(
            max(12, self.width() - toast.width() - 24),
            max(12, self.height() - toast.height() - 24),
        )
        toast.show()
        toast.raise_()
        self._toast = toast
        QTimer.singleShot(4200, toast.deleteLater)

    # -- shutdown -----------------------------------------------------------
    def closeEvent(self, event) -> None:  # noqa: N802
        log.info("Main window closing; stopping services.")
        try:
            active = self.active_page
            if active is not None:
                active.on_deactivated()
            self.context.monitoring.stop()
            self.context.processes.shutdown()
            self.context.history.stop()
        except Exception:
            log.exception("Error during shutdown")
        event.accept()
