"""Startup Applications: read-only review of sign-in entries."""

from __future__ import annotations

import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from nexus.core.startup_analyzer import StartupEntry, StartupScanResult
from nexus.platforms.macos.startup import startup_analyzer
from nexus.platforms.selection import platform_id
from nexus.services.background_task import BackgroundTask
from nexus.ui import theme
from nexus.ui.base import BasePage
from nexus.ui.widgets.common import (
    Badge,
    Banner,
    Card,
    PageScroll,
    SectionHeader,
    StatsRow,
    StatTile,
)
from nexus.ui.widgets.table import Column, RecordsModel, SearchProxy, configure_table
from nexus.utils import formatting
from nexus.utils.windows_shell import open_uri, reveal_in_explorer

STARTUP_SETTINGS_URI = "x-apple.systempreferences:com.apple.LoginItems-Settings.extension" if platform_id() == "macos" else "ms-settings:startupapps"


class StartupPage(BasePage):
    title = "Startup Applications"
    subtitle = "Review user login items and startup agents"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._task: BackgroundTask | None = None
        self._result: StartupScanResult | None = None
        self._selected: StartupEntry | None = None
        self._scanned_once = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = PageScroll()
        root.addWidget(scroll)
        content = scroll.content_layout

        header_card = Card("Startup overview")
        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        intro = QLabel(
            ("NEXUS lists property lists in your user LaunchAgents folder; it does not query whether each job is currently loaded. "
             "It never edits entries. Use System Settings > General > Login Items for changes.")
            if platform_id() == "macos" else
            ("NEXUS reads the supported Windows startup locations. It never edits, disables or "
             "removes entries. Use Windows Settings for changes.")
        )
        intro.setObjectName("muted")
        intro.setWordWrap(True)
        header_row.addWidget(intro, 1)
        self.settings_button = QPushButton("Open Login Items" if platform_id() == "macos" else "Open Windows Startup Apps")
        self.settings_button.setObjectName("primary")
        self.settings_button.clicked.connect(self._open_settings)
        header_row.addWidget(self.settings_button)
        self.rescan_button = QPushButton("Rescan")
        self.rescan_button.clicked.connect(self._start_scan)
        header_row.addWidget(self.rescan_button)
        header_card.body.addLayout(header_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.progress.setFixedHeight(4)
        header_card.body.addWidget(self.progress)
        content.addWidget(header_card)

        tiles = QHBoxLayout()
        tiles.setSpacing(12)
        self.total_tile = StatTile("Startup entries", "—", ("User LaunchAgents" if platform_id() == "macos" else "Registry and Startup folders"))
        self.user_tile = StatTile("Current user", "—", "Per-user entries")
        self.machine_tile = StatTile("All users", "—", ("System-wide entries" if platform_id() == "macos" else "Machine-wide entries"))
        self.missing_tile = StatTile("Missing targets", "—", "Executable not found")
        for tile in (self.total_tile, self.user_tile, self.machine_tile, self.missing_tile):
            tiles.addWidget(tile, 1)
        content.addLayout(tiles)

        self.error_banner = Banner("", level="warning")
        self.error_banner.setVisible(False)
        content.addWidget(self.error_banner)

        table_card = Card()
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search startup entries…")
        self.search.setClearButtonEnabled(True)
        self.search.setMaximumWidth(320)
        toolbar.addWidget(self.search, 1)
        self.scan_label = QLabel("Not scanned yet")
        self.scan_label.setObjectName("faint")
        toolbar.addWidget(self.scan_label)
        table_card.body.addLayout(toolbar)

        self.model = RecordsModel(
            [
                Column("Name", lambda e: e.name, width=200),
                Column("Source", lambda e: e.source, width=210),
                Column("Publisher", lambda e: e.publisher or "Unknown", width=170),
                Column(
                    "Status",
                    lambda e: e.status,
                    width=110,
                    color=lambda e: (
                        theme.current_palette().warning
                        if e.status == "Target missing"
                        else theme.current_palette().success
                        if e.status == "Registered"
                        else theme.current_palette().text_muted
                    ),
                ),
                Column(
                    "Impact",
                    lambda e: e.impact,
                    width=100,
                    color=lambda e: theme.current_palette().text_faint,
                ),
                Column("Executable", lambda e: e.executable or "Unresolved", width=280),
            ]
        )
        self.proxy = SearchProxy(self)
        self.proxy.setSourceModel(self.model)
        self.table = QTableView()
        configure_table(self.table, self.model, self.proxy)
        self.table.setMinimumHeight(320)
        table_card.body.addWidget(self.table)
        content.addWidget(table_card)

        detail_card = Card("Entry details")
        self.detail_placeholder = QLabel("Select an entry to see its command line and location.")
        self.detail_placeholder.setObjectName("muted")
        detail_card.body.addWidget(self.detail_placeholder)
        self.detail_panel = QWidget()
        detail_layout = QVBoxLayout(self.detail_panel)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(8)
        self.detail_name = QLabel("—")
        self.detail_name.setStyleSheet("font-size: 12pt; font-weight: 650;")
        self.detail_badge = Badge("Registered", "success")
        name_row = QHBoxLayout()
        name_row.addWidget(self.detail_name, 1)
        name_row.addWidget(self.detail_badge)
        detail_layout.addLayout(name_row)
        self.detail_grid = StatsRow(["Source", "Publisher", "Version", "File size"], columns=4)
        detail_layout.addWidget(self.detail_grid)
        self.detail_command = QLabel("")
        self.detail_command.setObjectName("muted")
        self.detail_command.setWordWrap(True)
        self.detail_command.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        detail_layout.addWidget(self.detail_command)
        self.detail_location = QLabel("")
        self.detail_location.setObjectName("faint")
        self.detail_location.setWordWrap(True)
        self.detail_location.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        detail_layout.addWidget(self.detail_location)
        actions = QHBoxLayout()
        self.locate_button = QPushButton("Open file location")
        self.locate_button.setObjectName("ghost")
        self.locate_button.clicked.connect(self._open_location)
        actions.addWidget(self.locate_button)
        actions.addStretch(1)
        self.impact_note = QLabel(
            "Per-entry startup impact is not estimated: Windows does not expose a supported measurement."
            if platform_id() == "windows" else
            "Per-entry startup impact is not estimated: macOS does not expose a supported measurement."
        )
        self.impact_note.setObjectName("faint")
        self.impact_note.setWordWrap(True)
        actions.addWidget(self.impact_note, 2)
        detail_layout.addLayout(actions)
        detail_card.body.addWidget(self.detail_panel)
        self.detail_panel.setVisible(False)
        content.addWidget(detail_card)
        content.addStretch(1)

        self.search.textChanged.connect(self.proxy.set_query)
        self.table.selectionModel().selectionChanged.connect(self._on_selection)

    # -- lifecycle ----------------------------------------------------------
    def on_activated(self) -> None:
        if not self._scanned_once:
            self._start_scan()

    def refresh_now(self) -> None:
        self._start_scan()

    def refresh_theme(self) -> None:
        if self._selected is not None:
            self._render_detail(self._selected)

    # -- scanning -----------------------------------------------------------
    def _start_scan(self) -> None:
        if self._task is not None and self._task.running:
            return
        self.rescan_button.setEnabled(False)
        self.progress.setVisible(True)
        self.scan_label.setText("Scanning startup locations…")
        self._task = BackgroundTask(startup_analyzer().scan, parent=self)
        self._task.finished.connect(self._on_scanned)
        self._task.failed.connect(self._on_scan_failed)
        self._task.start()

    def _on_scanned(self, result: StartupScanResult) -> None:
        self._scanned_once = True
        self._result = result
        self.progress.setVisible(False)
        self.rescan_button.setEnabled(True)
        self.scan_label.setText(
            f"Scanned in {result.duration_ms:.0f} ms · {len(result.entries)} entries"
        )
        self.model.set_records(list(result.entries))
        total = len(result.entries)
        user = sum(1 for entry in result.entries if entry.scope == "User")
        machine = total - user
        missing = sum(1 for entry in result.entries if entry.status == "Target missing")
        self.total_tile.set_value(str(total), "User LaunchAgent plists" if platform_id() == "macos" else "Registry and Startup folders")
        self.user_tile.set_value(str(user), "Per-user entries")
        self.machine_tile.set_value(str(machine), ("System-wide entries" if platform_id() == "macos" else "Machine-wide entries"))
        self.missing_tile.set_value(str(missing), "Executable not found")
        if result.errors:
            self.error_banner.text_label.setText(
                "Some locations could not be read: " + " · ".join(result.errors[:3])
                + (f" (+{len(result.errors) - 3} more)" if len(result.errors) > 3 else "")
            )
            self.error_banner.setVisible(True)
        else:
            self.error_banner.setVisible(False)
        if total == 0:
            self.scan_label.setText("No startup entries found")

    def _on_scan_failed(self, message: str) -> None:
        self.progress.setVisible(False)
        self.rescan_button.setEnabled(True)
        self.scan_label.setText("Scan failed")
        self.error_banner.text_label.setText(f"Startup entries could not be read: {message}")
        self.error_banner.setVisible(True)

    # -- details ------------------------------------------------------------
    def _on_selection(self, *_args) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        source = self.proxy.mapToSource(rows[0])
        entry = self.model.record_at(source.row())
        if entry is None:
            return
        self._selected = entry
        self._render_detail(entry)

    def _render_detail(self, entry: StartupEntry) -> None:
        self.detail_placeholder.setVisible(False)
        self.detail_panel.setVisible(True)
        self.detail_name.setText(entry.name)
        level = (
            "warning"
            if entry.status == "Target missing"
            else "success"
            if entry.status == "Registered"
            else "neutral"
        )
        self.detail_badge.setText(entry.status)
        self.detail_badge.set_level(level)
        self.detail_grid.set_values(
            {
                "Source": entry.source,
                "Publisher": entry.publisher or "Unknown",
                "Version": entry.file_version or "Unknown",
                "File size": (
                    formatting.format_bytes(entry.file_size_bytes)
                    if entry.file_size_bytes is not None
                    else "Unavailable"
                ),
            }
        )
        self.detail_command.setText(f"Command: {entry.command}")
        self.detail_location.setText(f"Location: {entry.location}")
        self.locate_button.setEnabled(bool(entry.executable))
        self.impact_note.setText(
            "Target exists on disk." if entry.file_exists else "Target file could not be found."
        )

    def _open_location(self) -> None:
        if self._selected is not None and self._selected.executable:
            reveal_in_explorer(self._selected.executable)

    def _open_settings(self) -> None:
        if not open_uri(STARTUP_SETTINGS_URI):
            window = self.window()
            if hasattr(window, "show_toast"):
                window.show_toast("Login Items settings could not be opened.", "warning")
