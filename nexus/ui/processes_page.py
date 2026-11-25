"""Process Manager: enumeration, search, details and confirmed termination."""

from __future__ import annotations

import os
import time
from collections import deque

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from nexus.core.process_manager import (
    ProcessInfo,
    assess_termination,
    read_process_details,
    terminate_process,
)
from nexus.services.background_task import BackgroundTask
from nexus.ui import theme
from nexus.ui.base import BasePage
from nexus.ui.widgets.charts import TimeSeriesChart
from nexus.ui.widgets.common import (
    Badge,
    Banner,
    Card,
    PageScroll,
    StatsRow,
    StatTile,
)
from nexus.ui.widgets.table import Column, RecordsModel, SearchProxy, configure_table
from nexus.utils import formatting
from nexus.platforms.selection import platform_id
from nexus.utils.windows_shell import reveal_in_explorer


class ProcessesPage(BasePage):
    title = "Processes"
    subtitle = "Inspect running applications and close them safely"

    def __init__(self, context) -> None:
        super().__init__(context)
        palette = theme.current_palette()
        self._selected_pid: int | None = None
        self._selected_info: ProcessInfo | None = None
        self._history: deque[tuple[float, float]] = deque(maxlen=90)
        self._tasks: list[BackgroundTask] = []
        self._last_processes: list[ProcessInfo] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = PageScroll()
        root.addWidget(scroll)
        content = scroll.content_layout

        tiles = QHBoxLayout()
        tiles.setSpacing(12)
        self.total_tile = StatTile("Running processes", "—", "Accessible to NEXUS")
        self.cpu_leader_tile = StatTile("Highest CPU", "—", "Instantaneous")
        self.mem_leader_tile = StatTile("Highest memory", "—", "Resident set size")
        self.protected_tile = StatTile("Protected", "—", "Termination blocked")
        for tile in (
            self.total_tile,
            self.cpu_leader_tile,
            self.mem_leader_tile,
            self.protected_tile,
        ):
            tiles.addWidget(tile, 1)
        content.addLayout(tiles)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(12)

        # Table ----------------------------------------------------------------
        table_card = Card()
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search by name, PID or path…")
        self.search.setClearButtonEnabled(True)
        self.search.setMaximumWidth(330)
        toolbar.addWidget(self.search, 1)
        self.count_label = QLabel("Waiting for data…")
        self.count_label.setObjectName("faint")
        toolbar.addWidget(self.count_label)
        self.refresh_button = QPushButton("Refresh")
        toolbar.addWidget(self.refresh_button)
        table_card.body.addLayout(toolbar)

        self.model = RecordsModel(
            [
                Column("Process", lambda p: p.name, width=190, color=lambda p: theme.current_palette().text_faint if p.is_protected else None),
                Column(
                    "PID",
                    lambda p: p.pid,
                    width=70,
                    align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                ),
                Column(
                    "CPU",
                    lambda p: p.cpu_percent,
                    formatter=lambda v: f"{v:.1f}%",
                    align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    color=lambda p: (
                        theme.current_palette().critical
                        if p.cpu_percent >= 50
                        else theme.current_palette().warning
                        if p.cpu_percent >= 20
                        else None
                    ),
                    width=80,
                ),
                Column(
                    "Memory",
                    lambda p: p.memory_rss,
                    formatter=formatting.format_bytes,
                    align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    width=100,
                ),
                Column(
                    "Memory %",
                    lambda p: p.memory_percent,
                    formatter=lambda v: f"{v:.1f}%",
                    align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    width=85,
                ),
                Column("Status", lambda p: p.status, width=100),
                Column("Executable path", lambda p: p.display_executable, tooltip=lambda p: p.executable or "Access denied"),
            ]
        )
        self.proxy = SearchProxy(self)
        self.proxy.setSourceModel(self.model)
        self.table = QTableView()
        configure_table(self.table, self.model, self.proxy)
        self.table.sortByColumn(2, Qt.SortOrder.DescendingOrder)
        self.table.setMinimumHeight(420)
        table_card.body.addWidget(self.table, 1)
        splitter.addWidget(table_card)

        # Details --------------------------------------------------------------
        detail_card = Card("Process details")
        self.detail_empty = QLabel("Select a process to inspect it.")
        self.detail_empty.setObjectName("muted")
        self.detail_empty.setWordWrap(True)
        detail_card.body.addWidget(self.detail_empty)

        self.detail_panel = QWidget()
        detail_layout = QVBoxLayout(self.detail_panel)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(8)
        self.detail_name = QLabel("—")
        self.detail_name.setStyleSheet("font-size: 13pt; font-weight: 650;")
        self.detail_name.setWordWrap(True)
        self.detail_pid = QLabel("PID —")
        self.detail_pid.setObjectName("faint")
        detail_layout.addWidget(self.detail_name)
        detail_layout.addWidget(self.detail_pid)
        self.detail_grid = StatsRow(["CPU", "Memory", "Status", "Started"], columns=2)
        detail_layout.addWidget(self.detail_grid)
        self.detail_path = QLabel("—")
        self.detail_path.setObjectName("faint")
        self.detail_path.setWordWrap(True)
        self.detail_path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        detail_layout.addWidget(self.detail_path)
        self.detail_badge = Badge("Select a process", "neutral")
        detail_layout.addWidget(self.detail_badge, 0, Qt.AlignmentFlag.AlignLeft)
        self.cpu_history = TimeSeriesChart(
            [("CPU", palette.accent)], max_points=90, y_max=100, height=90, fill=True
        )
        detail_layout.addWidget(self.cpu_history)
        self.detail_note = QLabel("")
        self.detail_note.setObjectName("faint")
        self.detail_note.setWordWrap(True)
        detail_layout.addWidget(self.detail_note)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        self.locate_button = QPushButton("Open location")
        self.locate_button.setObjectName("ghost")
        self.terminate_button = QPushButton("End task")
        self.terminate_button.setObjectName("danger")
        button_row.addWidget(self.locate_button)
        button_row.addWidget(self.terminate_button)
        button_row.addStretch(1)
        detail_layout.addLayout(button_row)
        detail_card.body.addWidget(self.detail_panel)
        detail_card.body.addStretch(1)
        self.detail_panel.setVisible(False)
        splitter.addWidget(detail_card)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([720, 360])
        content.addWidget(splitter, 1)

        safety = Banner(
            ("NEXUS only sends a graceful close request after you confirm. Critical macOS "
             "system processes are blocked, and nothing is terminated automatically.")
            if platform_id() == "macos" else
            ("NEXUS only sends a graceful close request after you confirm. Critical Windows "
             "processes are blocked, and nothing is ever terminated automatically."),
            level="info",
            icon_name="shield",
        )
        content.addWidget(safety)

        # wiring ---------------------------------------------------------------
        self.search.textChanged.connect(self.proxy.set_query)
        self.refresh_button.clicked.connect(self.context.processes.refresh_now)
        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.table.doubleClicked.connect(lambda _index: self._show_details_dialog())
        self.locate_button.clicked.connect(self._open_location)
        self.terminate_button.clicked.connect(self._confirm_termination)
        self.context.processes.sampleReady.connect(self._on_processes)
        self.context.processes.errorOccurred.connect(
            lambda message: self.window().show_toast(message, "error")
            if hasattr(self.window(), "show_toast")
            else None
        )

    # -- lifecycle ----------------------------------------------------------
    def on_activated(self) -> None:
        self.context.processes.set_active(True)
        if self.context.processes.latest:
            self._on_processes(self.context.processes.latest)

    def on_deactivated(self) -> None:
        self.context.processes.set_active(False)

    def refresh_now(self) -> None:
        self.context.processes.set_active(True)
        self.context.processes.refresh_now()

    def refresh_theme(self) -> None:
        self.cpu_history.apply_theme()
        if self._selected_pid is not None:
            self._select_pid(self._selected_pid)

    # -- table --------------------------------------------------------------
    def _on_processes(self, processes: list[ProcessInfo]) -> None:
        self._last_processes = processes
        self.model.set_records(processes)
        self.count_label.setText(f"{len(processes)} processes")
        if processes:
            cpu_leader = max(processes, key=lambda p: p.cpu_percent)
            mem_leader = max(processes, key=lambda p: p.memory_rss)
            protected = sum(1 for p in processes if p.is_protected)
            self.total_tile.set_value(str(len(processes)), "Visible to NEXUS")
            self.cpu_leader_tile.set_value(
                _short(cpu_leader.name), f"{cpu_leader.cpu_percent:.1f}% CPU · PID {cpu_leader.pid}"
            )
            self.mem_leader_tile.set_value(
                _short(mem_leader.name), f"{formatting.format_bytes(mem_leader.memory_rss)} · PID {mem_leader.pid}"
            )
            self.protected_tile.set_value(str(protected), "Blocked from termination")
        if self._selected_pid is not None:
            self._select_pid(self._selected_pid)

    def _on_selection_changed(self, *_args) -> None:
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return
        source = self.proxy.mapToSource(indexes[0])
        info = self.model.record_at(source.row())
        if info is None:
            return
        if info.pid != self._selected_pid:
            self._history.clear()
        self._selected_pid = info.pid
        self._selected_info = info
        self._render_details(info)

    def _select_pid(self, pid: int) -> None:
        info = next((p for p in self._last_processes if p.pid == pid), None)
        if info is None:
            self._selected_pid = None
            self._selected_info = None
            self.detail_panel.setVisible(False)
            self.detail_empty.setVisible(True)
            self.detail_empty.setText("The selected process has exited.")
            return
        self._selected_info = info
        for row in range(self.proxy.rowCount()):
            source = self.proxy.mapToSource(self.proxy.index(row, 0))
            record = self.model.record_at(source.row())
            if record is not None and record.pid == pid:
                with QSignalBlocker(self.table.selectionModel()):
                    self.table.selectRow(row)
                break
        self._render_details(info)

    def _render_details(self, info: ProcessInfo) -> None:
        self.detail_empty.setVisible(False)
        self.detail_panel.setVisible(True)
        assessment = assess_termination(info, current_pid=os.getpid())
        self.detail_name.setText(info.name)
        self.detail_pid.setText(f"PID {info.pid} · {info.username or 'owner unknown'}")
        self.detail_grid.set_values(
            {
                "CPU": f"{info.cpu_percent:.1f}%",
                "Memory": formatting.format_bytes(info.memory_rss),
                "Status": info.status,
                "Started": (
                    formatting.format_time_short(info.create_time)
                    if info.create_time
                    else "Unavailable"
                ),
            }
        )
        self.detail_path.setText(info.executable or "Executable path unavailable (access denied).")
        if info.is_protected:
            self.detail_badge.setText("Protected")
            self.detail_badge.set_level("warning")
        elif info.pid == os.getpid():
            self.detail_badge.setText("This application")
            self.detail_badge.set_level("info")
        else:
            self.detail_badge.setText("Eligible")
            self.detail_badge.set_level("success")
        can_terminate = assessment.allowed and not info.is_protected
        self.terminate_button.setEnabled(can_terminate)
        self.terminate_button.setToolTip(
            assessment.reason if not can_terminate else "Send a graceful close request after confirmation."
        )
        self.locate_button.setEnabled(bool(info.executable))
        self.detail_note.setText(assessment.caution or assessment.reason)
        self._history.append((time.time(), info.cpu_percent))
        points = [(ts, {"CPU": value}) for ts, value in self._history]
        self.cpu_history.set_values(points)

    # -- actions ------------------------------------------------------------
    def _open_location(self) -> None:
        info = self._selected_info
        if info is None or not info.executable:
            return
        if not reveal_in_explorer(info.executable):
            self._toast("The executable location could not be opened.", "warning")

    def _confirm_termination(self) -> None:
        info = self._selected_info
        if info is None:
            return
        assessment = assess_termination(info, current_pid=os.getpid())
        if not assessment.allowed:
            QMessageBox.information(
                self, "Not allowed", f"{info.name} cannot be terminated.\n\n{assessment.reason}"
            )
            return
        box = QMessageBox(self)
        box.setWindowTitle("End process")
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText(f"End {info.name} (PID {info.pid})?")
        informative = (
            "Any unsaved work in this application will be lost. NEXUS sends a graceful close "
            "request and waits a few seconds; it does not force-kill processes."
        )
        if assessment.caution:
            informative += f"\n\n{assessment.caution}"
        box.setInformativeText(informative)
        box.setDetailedText(
            f"Executable: {info.executable or 'access denied'}\n"
            f"CPU: {info.cpu_percent:.1f}%\n"
            f"Memory: {formatting.format_bytes(info.memory_rss)}\n"
            f"Status: {info.status}"
        )
        terminate = box.addButton("End process", QMessageBox.ButtonRole.DestructiveRole)
        cancel = box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(cancel)
        box.exec()
        if box.clickedButton() is not terminate:
            return
        self.terminate_button.setEnabled(False)
        task = BackgroundTask(
            terminate_process,
            info.pid,
            expected_name=info.name,
            expected_create_time=info.create_time,
            parent=self,
        )
        task.finished.connect(lambda result: self._on_termination_result(result))
        task.failed.connect(lambda message: self._on_termination_failed(message))
        self._tasks.append(task)
        task.start()

    def _on_termination_result(self, result) -> None:
        self._tasks = [task for task in self._tasks if task.running]
        level = "success" if result.success else "warning"
        self._toast(result.message, level)
        self.context.processes.refresh_now()
        if self._selected_info is not None:
            self._render_details(self._selected_info)

    def _on_termination_failed(self, message: str) -> None:
        self._tasks = [task for task in self._tasks if task.running]
        self._toast(f"Termination failed: {message}", "error")
        self.terminate_button.setEnabled(True)

    def _show_details_dialog(self) -> None:
        info = self._selected_info
        if info is None:
            return
        details = read_process_details(info.pid)
        if details is None:
            QMessageBox.information(
                self, "Process details", "The process exited or cannot be inspected."
            )
            return
        lines = [
            f"Name: {details.name}",
            f"PID: {details.pid}",
            f"Status: {details.status}",
            f"User: {details.username or 'Unavailable'}",
            f"CPU: {details.cpu_percent:.1f}%" if details.cpu_percent is not None else "CPU: Unavailable",
            f"Memory: {formatting.format_bytes(details.memory_rss)}" if details.memory_rss else "Memory: Unavailable",
            f"Threads: {details.threads if details.threads is not None else 'Unavailable'}",
            f"Connections: {details.connections if details.connections is not None else 'Unavailable'}",
            f"Started: {formatting.format_timestamp(details.create_time) if details.create_time else 'Unavailable'}",
            f"Executable: {details.executable or 'Access denied'}",
            f"Command line: {details.command_line or 'Unavailable'}",
            f"Working directory: {details.working_directory or 'Unavailable'}",
        ]
        box = QMessageBox(self)
        box.setWindowTitle(f"{details.name} — process details")
        box.setIcon(QMessageBox.Icon.Information)
        box.setText(f"{details.name} · PID {details.pid}")
        box.setInformativeText("Details are read live from Windows." if platform_id() == "windows" else "Details are read live from macOS.")
        box.setDetailedText("\n".join(lines))
        box.exec()

    def _toast(self, message: str, level: str = "info") -> None:
        window = self.window()
        if hasattr(window, "show_toast"):
            window.show_toast(message, level)


def _short(name: str) -> str:
    return name if len(name) <= 18 else name[:17] + "…"
