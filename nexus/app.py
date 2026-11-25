"""Application bootstrap: logging, services, theme and the main window."""

from __future__ import annotations

import logging
import os
import sys
import traceback
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QTimer
from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
)

from nexus import __app_name__, __version__
from nexus.core.gaming_session import GamingSessionRecorder
from nexus.database.connection import Database
from nexus.database.repository import HistoryRepository
from nexus.services.history_service import HistoryRecorder
from nexus.services.monitoring_service import MonitoringService
from nexus.services.process_service import ProcessService
from nexus.services.settings_service import SettingsService
from nexus.services.update_service import UpdateError, launch_installer
from nexus.platforms.selection import platform_id
from nexus.ui import icons, theme
from nexus.ui.context import AppContext
from nexus.ui.main_window import MainWindow
from nexus.utils.exceptions import DatabaseError, UnsupportedPlatformError
from nexus.utils.logging_config import configure_logging, get_logger
from nexus.utils.paths import logs_dir

log = get_logger(__name__)


class NexusApplication(QObject):
    """Owns long-lived services so the window can stay replaceable."""

    def __init__(self, app: QApplication, *, enable_wmi_sensors: bool = True) -> None:
        super().__init__()
        self.app = app
        self.settings = SettingsService()
        configure_logging(self.settings.current.log_level)
        self.theme_name = theme.apply_theme(app, self.settings.current.theme)

        log.info("Starting %s %s", __app_name__, __version__)
        if platform_id() == "windows":
            from nexus.hardware.windows import is_elevated, windows_build_number

            log.info(
                "Python %s | Windows build %s | elevated=%s",
                sys.version.split()[0],
                windows_build_number(),
                is_elevated(),
            )
        else:
            log.info("Python %s | macOS | least-privilege mode", sys.version.split()[0])

        self.repository, self.database_persistent = self._open_database()
        self.history = HistoryRecorder(
            self.repository,
            enabled=self.settings.current.store_history,
            retention_days=self.settings.current.retention_days,
        )
        self.history.start()
        self.monitoring = MonitoringService(
            interval_s=self.settings.current.refresh_interval_s,
            enable_wmi_sensors=enable_wmi_sensors,
        )
        self.processes = ProcessService(interval_ms=2000)
        self.gaming = GamingSessionRecorder()
        self.context = AppContext(
            settings=self.settings,
            monitoring=self.monitoring,
            processes=self.processes,
            repository=self.repository,
            history=self.history,
            gaming=self.gaming,
            database_persistent=self.database_persistent,
            theme_name=self.theme_name,
            install_update=self.install_update,
        )
        self.monitoring.snapshotReady.connect(self.history.handle_snapshot)
        self.window: MainWindow | None = None
        self.tray: QSystemTrayIcon | None = None
        self._shutdown_done = False
        self._shutdown_success = False
        app.aboutToQuit.connect(self.shutdown)

    # -- database -----------------------------------------------------------
    def _open_database(self) -> tuple[HistoryRepository, bool]:
        try:
            database = Database()
            repository = HistoryRepository(database)
            ok, detail = database.integrity_check()
            if not ok:
                raise DatabaseError(
                    f"SQLite integrity check failed: {detail}",
                    user_message="The performance history database appears to be damaged.",
                )
            log.info("History database ready at %s", database.path)
            return repository, True
        except DatabaseError as exc:
            log.exception("Database initialization failed")
            QMessageBox.warning(
                None,
                "Performance history unavailable",
                f"{exc.user_message}\n\nNEXUS will keep monitoring, but history will not be "
                f"saved to disk this session.\n\nTechnical detail: {exc}",
            )
            memory_database = Database(Path(":memory:"))
            return HistoryRepository(memory_database), False
        except Exception:
            log.exception("Unexpected database failure")
            message = (
                "NEXUS could not open the history database and will run without persistence."
            )
            QMessageBox.warning(None, "Performance history unavailable", message)
            return HistoryRepository(Database(Path(":memory:"))), False

    # -- window / tray ------------------------------------------------------
    def create_window(self, *, start_minimized: bool = False) -> MainWindow:
        window = MainWindow(self.app, self.context)
        self.window = window
        self._install_tray()
        self.monitoring.start()
        if start_minimized and self.tray is not None:
            self.tray.showMessage(
                __app_name__,
                "NEXUS is running in the notification area.",
                QSystemTrayIcon.MessageIcon.Information,
                3500,
            )
        else:
            window.show()
        return window

    def _install_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            log.info("System tray unavailable; start-minimized will show the window instead.")
            return
        tray = QSystemTrayIcon(icons.app_icon(), self)
        tray.setToolTip(f"{__app_name__} — performance monitor")
        menu = QMenu()
        show_action = QAction("Open NEXUS", menu)
        show_action.triggered.connect(self._show_window)
        diagnostics_action = QAction("Open logs folder", menu)
        diagnostics_action.triggered.connect(lambda: os.startfile(str(logs_dir())))
        pause_action = QAction("Pause monitoring", menu)
        pause_action.triggered.connect(self._toggle_monitoring)
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self.app.quit)
        menu.addAction(show_action)
        menu.addAction(pause_action)
        menu.addAction(diagnostics_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        tray.setContextMenu(menu)
        tray.activated.connect(self._on_tray_activated)
        tray.show()
        self.tray = tray

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._show_window()

    def _show_window(self) -> None:
        if self.window is None:
            return
        if self.window.isMinimized():
            self.window.showNormal()
        else:
            self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def _toggle_monitoring(self) -> None:
        if self.monitoring.running:
            self.monitoring.stop()
        else:
            self.monitoring.start()

    # -- shutdown -----------------------------------------------------------
    def shutdown(self) -> bool:
        if self._shutdown_done:
            return self._shutdown_success
        log.info("Shutting down NEXUS.")
        if not self.monitoring.stop():
            log.error("NEXUS shutdown aborted because the monitoring thread did not stop cleanly.")
            return False
        succeeded = True
        try:
            if not self.processes.shutdown():
                log.error("NEXUS shutdown aborted because process sampling did not stop cleanly.")
                return False
            if not self.history.stop():
                log.error("NEXUS shutdown aborted because history writes did not finish cleanly.")
                return False
            self.repository.close()
            if self.tray is not None:
                self.tray.hide()
        except Exception:
            succeeded = False
            log.exception("Error during application shutdown")
        self._shutdown_done = True
        self._shutdown_success = succeeded
        log.info("NEXUS stopped (clean=%s).", succeeded)
        return succeeded

    def install_update(self, installer_path: Path) -> bool:
        """Close application-owned state before launching the verified installer."""
        if not self.shutdown():
            return False
        try:
            if platform_id() != "windows":
                raise UpdateError("macOS updates are installed manually from a verified DMG.")
            launch_installer(installer_path)
        except UpdateError as exc:
            log.exception("Verified NEXUS installer could not be launched")
            QMessageBox.critical(
                self.window,
                "Update installer could not start",
                "NEXUS has closed its data services, but the installer could not be opened:\n\n"
                f"{exc}\n\nRestart NEXUS to resume monitoring.",
            )
            return False
        self.app.quit()
        return True


def _install_excepthook() -> None:
    original = sys.excepthook
    shown = {"once": False}

    def hook(exc_type, exc_value, exc_tb) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            original(exc_type, exc_value, exc_tb)
            return
        log.critical(
            "Unhandled exception:\n%s",
            "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
        )
        if not shown["once"] and QApplication.instance() is not None:
            shown["once"] = True
            QTimer.singleShot(
                0,
                lambda: QMessageBox.critical(
                    None,
                    "NEXUS encountered an error",
                    "An unexpected error occurred. Technical details were written to the log.\n\n"
                    f"{exc_type.__name__}: {exc_value}",
                ),
            )

    sys.excepthook = hook


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    try:
        selected_platform = platform_id()
    except UnsupportedPlatformError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(argv)
    app.setApplicationName(__app_name__)
    app.setApplicationDisplayName(__app_name__)
    app.setOrganizationName("NEXUS")
    app.setApplicationVersion(__version__)
    app.setWindowIcon(icons.app_icon())
    app.setQuitOnLastWindowClosed(True)
    _install_excepthook()

    enable_wmi = selected_platform == "windows" and "--no-wmi-sensors" not in argv
    try:
        configure_logging("INFO")
        bootstrap = NexusApplication(app, enable_wmi_sensors=enable_wmi)
        start_minimized = "--minimized" in argv or bootstrap.settings.current.start_minimized
        bootstrap.create_window(start_minimized=start_minimized)
        if "--smoke-test" in argv:
            QTimer.singleShot(4000, app.quit)
    except Exception as exc:
        log.exception("NEXUS could not start")
        QMessageBox.critical(
            None,
            "NEXUS could not start",
            "NEXUS was unable to initialize. Diagnostic details were written to the local "
            f"NEXUS log when available.\n\n{type(exc).__name__}: {exc}",
        )
        return 1
    return app.exec()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
