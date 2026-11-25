"""Settings: appearance, thresholds, history, exports and startup."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSignalBlocker, QTimer, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from nexus import __version__
from nexus.database.repository import StorageStats
from nexus.services.background_task import BackgroundTask
from nexus.services import update_service
from nexus.services.settings_service import LOG_LEVELS, REFRESH_INTERVALS, THEMES
from nexus.ui import theme
from nexus.ui.base import BasePage
from nexus.ui.widgets.common import (
    Badge,
    Banner,
    Card,
    Divider,
    PageScroll,
    SectionHeader,
)
from nexus.utils import formatting
from nexus.utils.paths import app_data_dir, default_export_dir, logs_dir
from nexus.utils.windows_shell import open_uri, reveal_in_explorer
from nexus.platforms.selection import platform_id


class SettingsPage(BasePage):
    title = "Settings"
    subtitle = "Monitoring, thresholds, storage and appearance"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._loading = False
        self._stats: StorageStats | None = None
        self._stats_task: BackgroundTask | None = None
        self._delete_task: BackgroundTask | None = None
        self._update_task: BackgroundTask | None = None
        self._pending_release = None
        self._verified_installer = None
        self._download_cancel = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = PageScroll()
        root.addWidget(scroll)
        content = scroll.content_layout

        content.addWidget(
            Banner(
                ("Changes take effect immediately and are saved locally. NEXUS never changes "
                 "Windows settings, services or scheduled tasks on its own.")
                if platform_id() == "windows" else
                "Changes take effect immediately and are saved locally. NEXUS does not change operating-system settings on its own.",
                level="info",
                icon_name="shield",
            )
        )

        # Appearance -----------------------------------------------------------
        appearance = Card("Appearance")
        self.theme_box = QComboBox()
        for mode in THEMES:
            self.theme_box.addItem(mode.capitalize(), mode)
        appearance.body.addLayout(_row("Theme", self.theme_box, "Dark is the default; System follows Windows." if platform_id() == "windows" else "Dark is the default; System follows the operating-system appearance."))

        self.interval_box = QComboBox()
        for seconds in REFRESH_INTERVALS:
            self.interval_box.addItem(f"Every {seconds} second{'s' if seconds != 1 else ''}", seconds)
        appearance.body.addLayout(
            _row("Refresh interval", self.interval_box, "How often hardware metrics are sampled.")
        )

        self.chart_points = QSpinBox()
        self.chart_points.setRange(30, 3600)
        self.chart_points.setSingleStep(30)
        self.chart_points.setSuffix(" points")
        appearance.body.addLayout(
            _row(
                "Chart history",
                self.chart_points,
                "Number of live samples kept in dashboard charts.",
            )
        )
        content.addWidget(appearance)

        # Thresholds -----------------------------------------------------------
        thresholds = Card("Warning thresholds")
        thresholds.body.addWidget(
            _hint(
                ("Thresholds drive recommendations and colour cues. They are not applied to Windows itself and never stop or change a process."
                 if platform_id() == "windows" else
                 "Thresholds drive recommendations and colour cues. They are not applied to the operating system and never stop or change a process.")
            )
        )
        self.cpu_threshold = _percent_spin(30.0, 100.0)
        thresholds.body.addLayout(_row("CPU warning", self.cpu_threshold, "Sustained utilization above this value."))
        self.memory_threshold = _percent_spin(30.0, 100.0)
        thresholds.body.addLayout(
            _row("Memory warning", self.memory_threshold, "Sustained physical memory usage above this value.")
        )
        self.storage_threshold = _percent_spin(1.0, 50.0)
        thresholds.body.addLayout(
            _row("Low free space", self.storage_threshold, "Free space below this percentage of a volume.")
        )
        content.addWidget(thresholds)

        # History --------------------------------------------------------------
        history = Card("Performance history")
        self.store_history = QCheckBox("Record measurements to the local database")
        history.body.addWidget(self.store_history)
        self.retention_spin = QSpinBox()
        self.retention_spin.setRange(1, 365)
        self.retention_spin.setSuffix(" days")
        history.body.addLayout(
            _row(
                "Retention",
                self.retention_spin,
                "Older rows are pruned automatically when NEXUS starts.",
            )
        )
        divider = Divider()
        history.body.addWidget(divider)
        stats_row = QHBoxLayout()
        stats_row.setSpacing(10)
        self.stats_label = QLabel("Reading database…")
        self.stats_label.setObjectName("muted")
        self.stats_label.setWordWrap(True)
        stats_row.addWidget(self.stats_label, 1)
        self.db_badge = Badge("—", "neutral")
        stats_row.addWidget(self.db_badge)
        self.refresh_stats_button = QPushButton("Refresh")
        self.refresh_stats_button.setObjectName("ghost")
        stats_row.addWidget(self.refresh_stats_button)
        history.body.addLayout(stats_row)
        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.open_data_button = QPushButton("Open data folder")
        self.open_data_button.setObjectName("ghost")
        actions.addWidget(self.open_data_button)
        actions.addStretch(1)
        self.delete_button = QPushButton("Delete all history")
        self.delete_button.setObjectName("danger")
        actions.addWidget(self.delete_button)
        history.body.addLayout(actions)
        content.addWidget(history)

        # Exports --------------------------------------------------------------
        exports = Card("Export locations")
        self.export_dir_input = QLineEdit()
        self.export_dir_input.setReadOnly(True)
        export_row = QHBoxLayout()
        export_row.setSpacing(8)
        export_row.addWidget(self.export_dir_input, 1)
        self.browse_export = QPushButton("Browse…")
        export_row.addWidget(self.browse_export)
        exports.body.addLayout(_row("Report exports", export_row, "Where reports and scans are saved by default."))
        self.reset_export = QPushButton("Reset to default")
        self.reset_export.setObjectName("ghost")
        exports.body.addWidget(self.reset_export, 0, Qt.AlignmentFlag.AlignLeft)
        content.addWidget(exports)

        # Application ----------------------------------------------------------
        application = Card("Application")
        self.start_minimized = QCheckBox("Start minimized to the notification area")
        application.body.addWidget(self.start_minimized)
        self.launch_at_startup = QCheckBox("Launch NEXUS when I sign in to Windows")
        self.launch_at_startup.setVisible(platform_id() == "windows")
        application.body.addWidget(self.launch_at_startup)
        application.body.addWidget(
            _hint(
                ("Startup uses a per-user HKCU Run entry only after you confirm. No admin rights, "
                 "services or scheduled tasks are used, and it can be removed here at any time.")
                if platform_id() == "windows" else
                "NEXUS reads current-user LaunchAgents. Manage login launch behavior in System Settings > General > Login Items."
                if platform_id() == "windows" else
                "NEXUS reads current-user LaunchAgents. Manage login launch behavior in System Settings ? General ? Login Items."
            )
        )
        self.startup_status = QLabel("")
        self.startup_status.setObjectName("faint")
        self.startup_status.setWordWrap(True)
        application.body.addWidget(self.startup_status)
        content.addWidget(application)

        # Software updates -----------------------------------------------------
        updates = Card("Software updates")
        self.auto_update_checks = QCheckBox("Check for updates automatically once a day")
        updates.body.addWidget(self.auto_update_checks)
        self.include_prereleases = QCheckBox("Include prerelease versions")
        updates.body.addWidget(self.include_prereleases)
        self.update_status = QLabel("")
        self.update_status.setObjectName("muted")
        self.update_status.setWordWrap(True)
        updates.body.addWidget(self.update_status)
        self.update_notes = QPlainTextEdit()
        self.update_notes.setReadOnly(True)
        self.update_notes.setMaximumHeight(130)
        self.update_notes.setPlaceholderText("Release notes will appear here when an update is available.")
        updates.body.addWidget(self.update_notes)
        update_actions = QHBoxLayout()
        self.check_updates_button = QPushButton("Check for Updates")
        self.check_updates_button.setObjectName("ghost")
        self.download_update_button = QPushButton("Download and Install" if platform_id() == "windows" else "Download Update DMG")
        self.download_update_button.setObjectName("primary")
        self.download_update_button.setEnabled(False)
        self.download_update_button.setVisible(False)
        self.cancel_update_button = QPushButton("Cancel download")
        self.cancel_update_button.setObjectName("ghost")
        self.cancel_update_button.setVisible(False)
        update_actions.addWidget(self.check_updates_button)
        update_actions.addWidget(self.download_update_button)
        update_actions.addWidget(self.cancel_update_button)
        update_actions.addStretch(1)
        updates.body.addLayout(update_actions)
        updates.body.addWidget(_hint(
            f"Current version: {__version__}. Checks are optional and use public GitHub Releases. "
            "No repository is configured for this build until its publisher sets one."
        ))
        content.addWidget(updates)

        # Diagnostics ----------------------------------------------------------
        diagnostics = Card("Diagnostics")
        self.log_level = QComboBox()
        self.log_level.addItems(LOG_LEVELS)
        diagnostics.body.addLayout(
            _row("Log level", self.log_level, "DEBUG is verbose; use it only while troubleshooting.")
        )
        diag_actions = QHBoxLayout()
        diag_actions.setSpacing(8)
        self.open_logs_button = QPushButton("Open log folder")
        self.open_logs_button.setObjectName("ghost")
        diag_actions.addWidget(self.open_logs_button)
        diag_actions.addStretch(1)
        diagnostics.body.addLayout(diag_actions)
        content.addWidget(diagnostics)

        # About ----------------------------------------------------------------
        about = Card("About")
        about.body.addWidget(
            SectionHeader(
                f"NEXUS {__version__}",
                ("Local-first Windows performance monitoring, diagnostics and safe optimization."
                 if platform_id() == "windows" else
                 "Local-first system monitoring, diagnostics and safe optimization."),
            )
        )
        self.about_label = QLabel("")
        self.about_label.setObjectName("muted")
        self.about_label.setWordWrap(True)
        self.about_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        about.body.addWidget(self.about_label)
        content.addWidget(about)
        content.addStretch(1)

        # wiring ---------------------------------------------------------------
        self.theme_box.currentIndexChanged.connect(
            lambda _index: self._apply(theme=self.theme_box.currentData())
        )
        self.interval_box.currentIndexChanged.connect(
            lambda _index: self._apply(refresh_interval_s=int(self.interval_box.currentData()))
        )
        self.chart_points.valueChanged.connect(
            lambda value: self._apply(chart_history_points=int(value))
        )
        self.cpu_threshold.valueChanged.connect(
            lambda value: self._apply(cpu_warning_threshold=float(value))
        )
        self.memory_threshold.valueChanged.connect(
            lambda value: self._apply(memory_warning_threshold=float(value))
        )
        self.storage_threshold.valueChanged.connect(
            lambda value: self._apply(storage_warning_threshold=float(value))
        )
        self.store_history.toggled.connect(
            lambda checked: self._apply(store_history=bool(checked))
        )
        self.retention_spin.valueChanged.connect(
            lambda value: self._apply(retention_days=int(value))
        )
        self.start_minimized.toggled.connect(
            lambda checked: self._apply(start_minimized=bool(checked))
        )
        self.log_level.currentTextChanged.connect(
            lambda level: self._apply(log_level=level)
        )
        self.launch_at_startup.toggled.connect(self._on_startup_toggled)
        self.browse_export.clicked.connect(self._browse_export)
        self.reset_export.clicked.connect(self._reset_export)
        self.open_data_button.clicked.connect(lambda: open_uri(str(app_data_dir())))
        self.open_logs_button.clicked.connect(lambda: open_uri(str(logs_dir())))
        self.refresh_stats_button.clicked.connect(self._refresh_stats)
        self.delete_button.clicked.connect(self._confirm_delete_history)
        self.check_updates_button.clicked.connect(self._check_for_updates)
        self.download_update_button.clicked.connect(self._confirm_update_download)
        self.cancel_update_button.clicked.connect(self._cancel_update_download)
        self.auto_update_checks.toggled.connect(self._on_auto_update_toggled)
        self.include_prereleases.toggled.connect(self._on_prereleases_toggled)
        self._auto_update_timer = QTimer(self)
        self._auto_update_timer.setInterval(24 * 60 * 60 * 1000)
        self._auto_update_timer.timeout.connect(self._check_for_updates)
        self.context.settings.changed.connect(self._on_settings_changed)

        self._load_values()
        self._refresh_stats()
        if self.context.settings.current.auto_update_checks:
            self._auto_update_timer.start()
            QTimer.singleShot(0, self._check_for_updates)

    # -- lifecycle ----------------------------------------------------------
    def on_activated(self) -> None:
        self._load_values()
        self._refresh_stats()
        self._refresh_startup_status()
        self.update_status.setText(
            f"Current version {__version__}. "
            f"Last check: {self.context.settings.current.last_update_check or 'Never'}"
        )
        if self.context.settings.current.auto_update_checks and not self._auto_update_timer.isActive():
            self._auto_update_timer.start()
            self._check_for_updates()

    def refresh_now(self) -> None:
        self._load_values()
        self._refresh_stats()

    def refresh_theme(self) -> None:
        self._refresh_startup_status()

    # -- values -------------------------------------------------------------
    def _load_values(self) -> None:
        self._loading = True
        try:
            settings = self.context.settings.current
            with QSignalBlocker(self.theme_box):
                index = self.theme_box.findData(settings.theme)
                self.theme_box.setCurrentIndex(max(0, index))
            with QSignalBlocker(self.interval_box):
                index = self.interval_box.findData(settings.refresh_interval_s)
                self.interval_box.setCurrentIndex(max(0, index))
            for widget, value in (
                (self.chart_points, settings.chart_history_points),
                (self.cpu_threshold, settings.cpu_warning_threshold),
                (self.memory_threshold, settings.memory_warning_threshold),
                (self.storage_threshold, settings.storage_warning_threshold),
                (self.retention_spin, settings.retention_days),
            ):
                with QSignalBlocker(widget):
                    widget.setValue(value)
            with QSignalBlocker(self.store_history):
                self.store_history.setChecked(settings.store_history)
            with QSignalBlocker(self.start_minimized):
                self.start_minimized.setChecked(settings.start_minimized)
            with QSignalBlocker(self.auto_update_checks):
                self.auto_update_checks.setChecked(settings.auto_update_checks)
            with QSignalBlocker(self.include_prereleases):
                self.include_prereleases.setChecked(settings.include_prereleases)
            with QSignalBlocker(self.launch_at_startup):
                self.launch_at_startup.setChecked(settings.launch_at_startup)
            with QSignalBlocker(self.log_level):
                self.log_level.setCurrentText(settings.log_level)
            self.export_dir_input.setText(settings.export_dir)
        finally:
            self._loading = False
        if platform_id() == "windows":
            from nexus.hardware.windows import is_elevated, windows_build_number
            platform_details = (
                f"Windows build {windows_build_number()} ? "
                f"{'Elevated' if is_elevated() else 'Standard user (no admin rights)'}"
            )
        else:
            import platform
            platform_details = f"macOS {platform.mac_ver()[0]} ? {platform.machine()} ? Standard user"
        self.about_label.setText(
            f"Version {__version__} ? Python {os.sys.version.split()[0]} ? {platform_details}\n"
            f"Data folder: {app_data_dir()}\nNEXUS collects data locally and uploads nothing."
        )
        self._refresh_startup_status()

    def _apply(self, **changes) -> None:
        if self._loading:
            return
        try:
            self.context.settings.update(**changes)
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Setting not applied",
                f"That value could not be saved:\n\n{exc}",
            )
            self._load_values()

    def _on_settings_changed(self, settings) -> None:
        if not self._loading:
            self._load_values()

    def _refresh_startup_status(self) -> None:
        if platform_id() == "macos":
            self.startup_status.setText("Login Items are read-only in this version. Manage NEXUS in System Settings ? General ? Login Items.")
            self.startup_status.setStyleSheet(f"color: {theme.current_palette().text_faint};")
            return
        try:
            from nexus.services import startup_registration
            registered = startup_registration.is_registered()
        except Exception:
            registered = False
        if registered:
            self.startup_status.setText(
                "A per-user startup entry is currently registered for NEXUS."
            )
            self.startup_status.setStyleSheet(f"color: {theme.current_palette().success};")
        else:
            self.startup_status.setText("No NEXUS startup entry is registered.")
            self.startup_status.setStyleSheet(f"color: {theme.current_palette().text_faint};")

    # -- history ------------------------------------------------------------
    def _refresh_stats(self) -> None:
        if self._stats_task is not None and self._stats_task.running:
            return
        repository = self.context.repository

        def work() -> StorageStats:
            return repository.storage_stats()

        self.refresh_stats_button.setEnabled(False)
        self._stats_task = BackgroundTask(work, parent=self)
        self._stats_task.finished.connect(self._on_stats)
        self._stats_task.failed.connect(self._on_stats_failed)
        self._stats_task.start()

    def _on_stats(self, stats: StorageStats) -> None:
        self.refresh_stats_button.setEnabled(True)
        self._stats = stats
        if stats.rows:
            self.stats_label.setText(
                f"{stats.rows:,} stored rows · {formatting.format_bytes(stats.file_size_bytes)} · "
                f"{formatting.format_timestamp(stats.oldest_ts)} → "
                f"{formatting.format_timestamp(stats.newest_ts)}"
            )
            self.db_badge.setText("Ready")
            self.db_badge.set_level("success")
        else:
            self.stats_label.setText("The database is empty. History appears once monitoring records a sample.")
            self.db_badge.setText("Empty")
            self.db_badge.set_level("neutral")

    def _on_stats_failed(self, message: str) -> None:
        self.refresh_stats_button.setEnabled(True)
        self.stats_label.setText(f"Database could not be read: {message}")
        self.db_badge.setText("Error")
        self.db_badge.set_level("warning")

    def _confirm_delete_history(self) -> None:
        if self._delete_task is not None and self._delete_task.running:
            return
        box = QMessageBox(self)
        box.setWindowTitle("Delete all history")
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText("Delete every stored measurement?")
        box.setInformativeText(
            "This permanently removes the local performance history and saved gaming sessions. "
            "Live monitoring keeps running. This cannot be undone."
        )
        delete = box.addButton("Delete history", QMessageBox.ButtonRole.DestructiveRole)
        cancel = box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(cancel)
        box.exec()
        if box.clickedButton() is not delete:
            return
        repository = self.context.repository
        self.delete_button.setEnabled(False)
        self.stats_label.setText("Deleting stored history…")

        def work() -> int:
            removed = repository.delete_all_metrics()
            repository.delete_all_gaming_sessions()
            return removed

        self._delete_task = BackgroundTask(work, parent=self)
        self._delete_task.finished.connect(self._on_deleted)
        self._delete_task.failed.connect(self._on_delete_failed)
        self._delete_task.start()

    def _on_deleted(self, removed: int) -> None:
        self.delete_button.setEnabled(True)
        self.stats_label.setText(f"Deleted {removed:,} stored rows.")
        window = self.window()
        if hasattr(window, "show_toast"):
            window.show_toast("Performance history deleted.", "success")
        self._refresh_stats()

    def _on_delete_failed(self, message: str) -> None:
        self.delete_button.setEnabled(True)
        self.stats_label.setText(f"History could not be deleted: {message}")

    # -- software updates ---------------------------------------------------
    def _check_for_updates(self) -> None:
        if self._update_task is not None and self._update_task.running:
            return
        try:
            repository = update_service.configured_repository()
        except update_service.UpdateError as exc:
            self.update_status.setText(str(exc))
            return
        if repository is None:
            self.update_status.setText(
                f"Updates are not configured for this build. Current version: {__version__}."
            )
            return
        self.check_updates_button.setEnabled(False)
        self.download_update_button.setVisible(False)
        self.update_status.setText("Checking for updates…")
        task = BackgroundTask(
            update_service.check_latest_release,
            allow_prerelease=self.include_prereleases.isChecked(),
            parent=self,
        )
        self._update_task = task
        task.finished.connect(self._on_update_check_finished)
        task.failed.connect(self._on_update_check_failed)
        task.start()

    def _on_update_check_finished(self, release) -> None:
        self.check_updates_button.setEnabled(True)
        checked_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
        try:
            self.context.settings.update(last_update_check=checked_at)
        except Exception:
            pass
        if release is None:
            self._pending_release = None
            self.update_status.setText(f"NEXUS {__version__} is up to date. Last check: {checked_at}")
            self.update_notes.clear()
            return
        self._pending_release = release
        self.update_status.setText(
            f"NEXUS {release.version} is available (installed: {__version__}). "
            f"Last check: {checked_at}"
        )
        self.update_notes.setPlainText(release.notes)
        self.download_update_button.setVisible(True)
        self.download_update_button.setEnabled(True)

    def _on_update_check_failed(self, message: str) -> None:
        self.check_updates_button.setEnabled(True)
        self.update_status.setText(f"Update check failed: {message}")

    def _confirm_update_download(self) -> None:
        release = self._pending_release
        if release is None:
            return
        is_macos = platform_id() == "macos"
        answer = QMessageBox.question(
            self,
            "Download NEXUS update",
            (f"Download the NEXUS {release.version} DMG?\n\n"
             "NEXUS will verify its SHA-256 checksum. Open the DMG and drag NEXUS.app to Applications to update.")
            if is_macos else
            (f"Download and open the NEXUS {release.version} installer?\n\n"
             "The downloaded installer will be checked against the release SHA-256 checksum. "
             "Checksum verification confirms file integrity, not publisher identity. "
             "The normal installer wizard will ask you to continue."),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.download_update_button.setEnabled(False)
        self.cancel_update_button.setVisible(True)
        self.check_updates_button.setEnabled(False)
        self.update_status.setText(f"Downloading and verifying NEXUS {release.version}…")
        import threading

        self._download_cancel = threading.Event()
        task = BackgroundTask(
            update_service.download_verified_installer,
            release,
            cancel_event=self._download_cancel,
            parent=self,
        )
        self._update_task = task
        task.finished.connect(self._on_update_download_finished)
        task.failed.connect(self._on_update_download_failed)
        task.start()

    def _cancel_update_download(self) -> None:
        if self._download_cancel is not None:
            self._download_cancel.set()
            self.cancel_update_button.setEnabled(False)
            self.update_status.setText("Cancelling update download…")

    def _on_auto_update_toggled(self, enabled: bool) -> None:
        if self._loading:
            return
        try:
            self.context.settings.update(auto_update_checks=bool(enabled))
        except Exception as exc:
            self.update_status.setText(f"Could not save update preference: {exc}")
            self._load_values()
            return
        if enabled:
            self._auto_update_timer.start()
            self._check_for_updates()
        else:
            self._auto_update_timer.stop()

    def _on_prereleases_toggled(self, enabled: bool) -> None:
        if self._loading:
            return
        try:
            self.context.settings.update(include_prereleases=bool(enabled))
        except Exception as exc:
            self.update_status.setText(f"Could not save update preference: {exc}")
            self._load_values()

    def _on_update_download_finished(self, path) -> None:
        self.check_updates_button.setEnabled(True)
        self.cancel_update_button.setVisible(False)
        self._verified_installer = path
        if platform_id() == "macos":
            self.update_status.setText(f"DMG verified and saved to {path}. Open it, then drag NEXUS.app to Applications.")
            self.download_update_button.setEnabled(True)
            if open_uri(str(path)):
                self.update_status.setText(f"DMG verified and opened. Drag NEXUS.app to Applications to complete the update. File: {path}")
            return
        if self.context.install_update is None:
            self.update_status.setText(
                f"Installer verified and saved at {path}, but safe application handoff is unavailable."
            )
            self.download_update_button.setEnabled(True)
            return
        if not self.context.install_update(path):
            self.update_status.setText(
                "The verified installer is saved, but NEXUS could not shut down cleanly. "
                "The update was not launched. Check the local log before retrying."
            )
            self.download_update_button.setEnabled(True)
            return
        self.update_status.setText("Installer launched. Follow its wizard to complete the update.")

    def _on_update_download_failed(self, message: str) -> None:
        self.check_updates_button.setEnabled(True)
        self.download_update_button.setEnabled(True)
        self.cancel_update_button.setVisible(False)
        self.cancel_update_button.setEnabled(True)
        self.update_status.setText(f"Update download or verification failed: {message}")

    # -- startup ------------------------------------------------------------
    def _on_startup_toggled(self, checked: bool) -> None:
        if self._loading:
            return
        if platform_id() != "windows":
            return
        if checked:
            box = QMessageBox(self)
            box.setWindowTitle("Add startup entry")
            box.setIcon(QMessageBox.Icon.Question)
            box.setText("Launch NEXUS when you sign in?")
            box.setInformativeText(
                "NEXUS will add a per-user entry under "
                "HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run. "
                "It starts minimized and can be removed here at any time. No administrator "
                "rights are required."
            )
            confirm = box.addButton("Add startup entry", QMessageBox.ButtonRole.AcceptRole)
            cancel = box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
            box.setDefaultButton(cancel)
            box.exec()
            if box.clickedButton() is not confirm:
                with QSignalBlocker(self.launch_at_startup):
                    self.launch_at_startup.setChecked(False)
                return
            try:
                startup_registration.register()
                self.context.settings.update(launch_at_startup=True)
            except Exception as exc:
                QMessageBox.warning(
                    self, "Startup entry not added", f"Windows rejected the change:\n\n{exc}"
                )
                with QSignalBlocker(self.launch_at_startup):
                    self.launch_at_startup.setChecked(False)
        else:
            box = QMessageBox(self)
            box.setWindowTitle("Remove startup entry")
            box.setIcon(QMessageBox.Icon.Question)
            box.setText("Remove the NEXUS startup entry?")
            box.setInformativeText("NEXUS will no longer start when you sign in.")
            remove = box.addButton("Remove entry", QMessageBox.ButtonRole.DestructiveRole)
            cancel = box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
            box.setDefaultButton(cancel)
            box.exec()
            if box.clickedButton() is not remove:
                with QSignalBlocker(self.launch_at_startup):
                    self.launch_at_startup.setChecked(True)
                return
            try:
                startup_registration.unregister()
                self.context.settings.update(launch_at_startup=False)
            except Exception as exc:
                QMessageBox.warning(
                    self, "Startup entry not removed", f"Windows rejected the change:\n\n{exc}"
                )
                with QSignalBlocker(self.launch_at_startup):
                    self.launch_at_startup.setChecked(True)
        self._refresh_startup_status()

    # -- export path --------------------------------------------------------
    def _browse_export(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Choose export folder", self.context.settings.current.export_dir
        )
        if not folder:
            return
        self.export_dir_input.setText(folder)
        self._apply(export_dir=folder, gaming_report_dir=folder)

    def _reset_export(self) -> None:
        default = str(default_export_dir())
        self.export_dir_input.setText(default)
        self._apply(export_dir=default, gaming_report_dir=default)


def _row(label: str, widget: QWidget | QHBoxLayout, hint: str = "") -> QHBoxLayout:
    layout = QHBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(12)
    name = QLabel(label)
    name.setObjectName("muted")
    name.setFixedWidth(150)
    layout.addWidget(name, 0, Qt.AlignmentFlag.AlignTop)
    holder = QVBoxLayout()
    holder.setContentsMargins(0, 0, 0, 0)
    holder.setSpacing(3)
    if isinstance(widget, QHBoxLayout):
        holder.addLayout(widget)
    else:
        widget.setMaximumWidth(280)
        holder.addWidget(widget, 0, Qt.AlignmentFlag.AlignLeft)
    if hint:
        hint_label = _hint(hint)
        holder.addWidget(hint_label)
    layout.addLayout(holder, 1)
    return layout


def _hint(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("faint")
    label.setWordWrap(True)
    return label


def _percent_spin(low: float, high: float) -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setRange(low, high)
    spin.setDecimals(0)
    spin.setSingleStep(1.0)
    spin.setSuffix(" %")
    spin.setMaximumWidth(140)
    return spin
