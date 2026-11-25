"""Storage Analyzer: cancellable background folder scan and exports."""

from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from nexus.core.storage_scanner import (
    CategoryUsage,
    DirectoryRecord,
    FileRecord,
    ScanProgress,
    ScanResult,
    StorageScanner,
)
from nexus.services.background_task import BackgroundTask
from nexus.ui import theme
from nexus.ui.base import BasePage
from nexus.ui.widgets.charts import HBarChart, PieChart
from nexus.ui.widgets.common import (
    Banner,
    Card,
    PageScroll,
    SectionHeader,
    StatTile,
)
from nexus.ui.widgets.table import Column, RecordsModel, SearchProxy, configure_table
from nexus.utils import formatting
from nexus.utils.windows_shell import reveal_in_explorer

PIE_COLORS = ("#6366F1", "#22C55E", "#F59E0B", "#EF4444", "#8B5CF6", "#06B6D4", "#EC4899", "#64748B")


class StoragePage(BasePage):
    title = "Storage Analyzer"
    subtitle = "Understand what occupies disk space"

    scanProgress = Signal(object)

    def __init__(self, context) -> None:
        super().__init__(context)
        self._task: BackgroundTask | None = None
        self._cancel_event: threading.Event | None = None
        self._result: ScanResult | None = None
        self._scanning = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = PageScroll()
        root.addWidget(scroll)
        content = scroll.content_layout

        controls = Card("Scan a folder")
        row = QHBoxLayout()
        row.setSpacing(8)
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText(r"Choose a folder, for example C:\Users\you\Downloads")
        self.path_input.setText(str(Path.home()))
        row.addWidget(self.path_input, 1)
        self.browse_button = QPushButton("Browse…")
        self.browse_button.clicked.connect(self._browse)
        row.addWidget(self.browse_button)
        self.scan_button = QPushButton("Scan folder")
        self.scan_button.setObjectName("primary")
        self.scan_button.clicked.connect(self._start_scan)
        row.addWidget(self.scan_button)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("danger")
        self.cancel_button.setVisible(False)
        self.cancel_button.clicked.connect(self._cancel_scan)
        row.addWidget(self.cancel_button)
        controls.body.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.progress.setFixedHeight(5)
        controls.body.addWidget(self.progress)
        note = QLabel(
            "Scans are read-only and run on a background thread. Symbolic links and junctions are "
            "skipped to prevent loops; NEXUS never deletes files."
        )
        note.setObjectName("faint")
        note.setWordWrap(True)
        controls.body.addWidget(note)
        content.addWidget(controls)

        tiles = QHBoxLayout()
        tiles.setSpacing(12)
        self.size_tile = StatTile("Total size", "—", "Files scanned")
        self.files_tile = StatTile("Files", "—", "Regular files")
        self.dirs_tile = StatTile("Directories", "—", "Folders visited")
        self.time_tile = StatTile("Scan time", "—", "Wall clock")
        self.skipped_tile = StatTile("Safety skips", "—", "Links and system folders")
        for tile in (self.size_tile, self.files_tile, self.dirs_tile, self.time_tile, self.skipped_tile):
            tiles.addWidget(tile, 1)
        content.addLayout(tiles)

        self.status_banner = Banner("Choose a folder and start a scan.", level="info", icon_name="info")
        content.addWidget(self.status_banner)

        charts_row = QHBoxLayout()
        charts_row.setSpacing(14)
        folders_card = Card("Largest folders")
        self.folder_bars = HBarChart(rows=7)
        folders_card.body.addWidget(self.folder_bars)
        charts_row.addWidget(folders_card, 3)

        types_card = Card("File type distribution")
        self.pie = PieChart()
        types_card.body.addWidget(self.pie)
        charts_row.addWidget(types_card, 2)
        content.addLayout(charts_row)

        results_card = Card()
        header = SectionHeader("Scan results", "Largest folders and files found in the selected location.")
        self.export_csv_button = QPushButton("Export CSV")
        self.export_csv_button.setObjectName("ghost")
        self.export_csv_button.setEnabled(False)
        self.export_csv_button.clicked.connect(lambda: self._export("csv"))
        self.export_json_button = QPushButton("Export JSON")
        self.export_json_button.setObjectName("ghost")
        self.export_json_button.setEnabled(False)
        self.export_json_button.clicked.connect(lambda: self._export("json"))
        header.add_action(self.export_csv_button)
        header.add_action(self.export_json_button)
        results_card.body.addWidget(header)

        search_row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter results by path or extension…")
        self.search.setClearButtonEnabled(True)
        self.search.setMaximumWidth(360)
        search_row.addWidget(self.search, 1)
        self.open_button = QPushButton("Open selected location")
        self.open_button.setObjectName("ghost")
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self._open_selected)
        search_row.addWidget(self.open_button)
        results_card.body.addLayout(search_row)

        self.tabs = QTabWidget()
        self.folder_model = RecordsModel(
            [
                Column("Folder", lambda r: r.path),
                Column(
                    "Size",
                    lambda r: r.size,
                    formatter=formatting.format_bytes,
                    align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    width=110,
                ),
                Column(
                    "Share",
                    lambda r: r.size,
                    formatter=lambda v: f"{100.0 * v / max(1, self._total_bytes):.1f}%",
                    align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    width=80,
                ),
            ]
        )
        self.folder_proxy = SearchProxy(self)
        self.folder_proxy.setSourceModel(self.folder_model)
        self.folder_table = QTableView()
        configure_table(self.folder_table, self.folder_model, self.folder_proxy)
        self.folder_table.setMinimumHeight(230)
        self.tabs.addTab(self.folder_table, "Largest folders")

        self.file_model = RecordsModel(
            [
                Column("File", lambda r: r.path),
                Column(
                    "Size",
                    lambda r: r.size,
                    formatter=formatting.format_bytes,
                    align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    width=110,
                ),
            ]
        )
        self.file_proxy = SearchProxy(self)
        self.file_proxy.setSourceModel(self.file_model)
        self.file_table = QTableView()
        configure_table(self.file_table, self.file_model, self.file_proxy)
        self.file_table.setMinimumHeight(230)
        self.tabs.addTab(self.file_table, "Largest files")

        self.category_model = RecordsModel(
            [
                Column("Category", lambda c: c.name),
                Column(
                    "Files",
                    lambda c: c.files,
                    formatter=str,
                    align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                ),
                Column(
                    "Size",
                    lambda c: c.bytes,
                    formatter=formatting.format_bytes,
                    align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                ),
            ]
        )
        self.category_table = QTableView()
        configure_table(self.category_table, self.category_model)
        self.category_table.setMinimumHeight(230)
        self.tabs.addTab(self.category_table, "File types")
        results_card.body.addWidget(self.tabs)
        content.addWidget(results_card)
        content.addStretch(1)

        self.scanProgress.connect(self._on_progress)
        self.search.textChanged.connect(self._apply_filter)
        self.folder_table.selectionModel().selectionChanged.connect(self._on_selection)
        self.file_table.selectionModel().selectionChanged.connect(self._on_selection)
        self.folder_table.doubleClicked.connect(lambda _i: self._open_selected())
        self.file_table.doubleClicked.connect(lambda _i: self._open_selected())
        self._apply_filter("")

    # -- scanning -----------------------------------------------------------
    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose a folder to scan", self.path_input.text())
        if folder:
            self.path_input.setText(folder)

    def _start_scan(self) -> None:
        if self._scanning:
            return
        path = self.path_input.text().strip()
        if not path:
            self._set_status("Choose a folder to scan.", "warning")
            return
        target = Path(path)
        if not target.exists():
            self._set_status(f"The folder does not exist: {target}", "warning")
            return
        if not target.is_dir():
            self._set_status("The selected path is not a folder.", "warning")
            return
        self._cancel_event = threading.Event()
        self._scanning = True
        self.scan_button.setEnabled(False)
        self.browse_button.setEnabled(False)
        self.cancel_button.setVisible(True)
        self.cancel_button.setEnabled(True)
        self.progress.setVisible(True)
        self.export_csv_button.setEnabled(False)
        self.export_json_button.setEnabled(False)
        self._set_status(f"Scanning {target}…", "info")

        scanner = StorageScanner(
            top_files=80,
            top_directories=80,
            cancel_event=self._cancel_event,
            progress_callback=self.scanProgress.emit,
        )
        task = BackgroundTask(scanner.scan, target, parent=self)
        task.finished.connect(self._on_scan_finished)
        task.failed.connect(self._on_scan_failed)
        self._task = task
        task.start()

    def _cancel_scan(self) -> None:
        if self._cancel_event is not None:
            self._cancel_event.set()
            self.cancel_button.setEnabled(False)
            self._set_status("Cancelling scan…", "warning")

    def _on_progress(self, progress: ScanProgress) -> None:
        self._set_status(
            f"Scanning… {progress.files:,} files · {progress.directories:,} folders · "
            f"{formatting.format_bytes(progress.bytes)}",
            "info",
        )
        self.progress.setToolTip(progress.current_path)

    def _on_scan_finished(self, result: ScanResult) -> None:
        self._scanning = False
        self.scan_button.setEnabled(True)
        self.browse_button.setEnabled(True)
        self.cancel_button.setVisible(False)
        self.progress.setVisible(False)
        if result.cancelled:
            self._set_status("Scan cancelled. Previous results were kept.", "warning")
            return
        self._result = result
        self._total_bytes = max(1, result.total_bytes)
        self.size_tile.set_value(formatting.format_bytes(result.total_bytes), result.root)
        self.files_tile.set_value(f"{result.total_files:,}", "Regular files")
        self.dirs_tile.set_value(f"{result.total_directories:,}", "Folders visited")
        self.time_tile.set_value(f"{result.duration_seconds:.1f}s", "Wall clock")
        self.skipped_tile.set_value(
            str(result.skipped_links + result.skipped_system_dirs),
            f"{result.skipped_links} links · {result.skipped_system_dirs} system",
        )
        self.folder_model.set_records(list(result.largest_directories))
        self.file_model.set_records(list(result.largest_files))
        self.category_model.set_records(list(result.categories))
        self.folder_bars.set_data(
            [(Path(record.path).name or record.path, record.size) for record in result.largest_directories[:7]]
        )
        colors = [
            (category.name, category.bytes, PIE_COLORS[index % len(PIE_COLORS)])
            for index, category in enumerate(result.categories)
        ]
        self.pie.set_data(colors)
        self.export_csv_button.setEnabled(True)
        self.export_json_button.setEnabled(True)
        total_text = formatting.format_bytes(result.total_bytes)
        if result.truncated:
            self._set_status(
                f"Scan stopped at the safety limit. Partial total: {total_text}.", "warning"
            )
        elif result.errors:
            self._set_status(
                f"Scan complete: {total_text} in {result.duration_seconds:.1f}s. "
                f"{result.error_count} locations were inaccessible (see tooltip).",
                "warning",
            )
            self.status_banner.setToolTip("\n".join(result.errors))
        else:
            self._set_status(
                f"Scan complete: {total_text} across {result.total_files:,} files in "
                f"{result.duration_seconds:.1f}s.",
                "success",
            )
        self._apply_filter(self.search.text())

    def _on_scan_failed(self, message: str) -> None:
        self._scanning = False
        self.scan_button.setEnabled(True)
        self.browse_button.setEnabled(True)
        self.cancel_button.setVisible(False)
        self.progress.setVisible(False)
        self._set_status(f"Scan failed: {message}", "error")

    # -- results ------------------------------------------------------------
    @property
    def _total_bytes(self) -> int:
        return getattr(self, "_scan_total", 1)

    @_total_bytes.setter
    def _total_bytes(self, value: int) -> None:
        self._scan_total = value

    def _apply_filter(self, text: str) -> None:
        self.folder_proxy.set_query(text)
        self.file_proxy.set_query(text)

    def _on_selection(self, *_args) -> None:
        self.open_button.setEnabled(self._selected_path() is not None)

    def _selected_path(self) -> str | None:
        if self.tabs.currentIndex() == 0:
            rows = self.folder_table.selectionModel().selectedRows()
            model, proxy = self.folder_model, self.folder_proxy
        elif self.tabs.currentIndex() == 1:
            rows = self.file_table.selectionModel().selectedRows()
            model, proxy = self.file_model, self.file_proxy
        else:
            return None
        if not rows:
            return None
        source = proxy.mapToSource(rows[0])
        record = model.record_at(source.row())
        if isinstance(record, (DirectoryRecord, FileRecord)):
            return record.path
        return None

    def _open_selected(self) -> None:
        path = self._selected_path()
        if path is None:
            return
        candidate = Path(path)
        if candidate.is_dir():
            reveal_in_explorer(str(candidate))
        else:
            reveal_in_explorer(str(candidate))

    def _set_status(self, message: str, level: str) -> None:
        object_name = {
            "info": "innerCard",
            "warning": "warningBanner",
            "error": "dangerBanner",
            "success": "innerCard",
        }[level]
        self.status_banner.text_label.setText(message)
        self.status_banner.setObjectName(object_name)
        self.status_banner.style().unpolish(self.status_banner)
        self.status_banner.style().polish(self.status_banner)

    # -- export -------------------------------------------------------------
    def _export(self, kind: str) -> None:
        if self._result is None:
            return
        settings = self.context.settings.current
        default_dir = Path(settings.export_dir)
        try:
            default_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            default_dir = Path.home()
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"nexus-storage-{stamp}.{kind}"
        path, _ = QFileDialog.getSaveFileName(
            self,
            f"Export storage scan ({kind.upper()})",
            str(default_dir / filename),
            f"{kind.upper()} files (*.{kind})",
        )
        if not path:
            return
        content = self._result.to_csv() if kind == "csv" else self._result.to_json()
        try:
            Path(path).write_text(content, encoding="utf-8-sig" if kind == "csv" else "utf-8")
        except OSError as exc:
            self._set_status(f"Export failed: {exc}", "error")
            return
        window = self.window()
        if hasattr(window, "show_toast"):
            window.show_toast(f"Exported to {path}", "success")
        self._set_status(f"Exported {kind.upper()} to {path}", "success")
