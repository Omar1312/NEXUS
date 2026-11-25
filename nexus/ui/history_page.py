"""Performance History: locally stored measurements and trends."""

from __future__ import annotations

import time
from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableView,
    QVBoxLayout,
)

from nexus.database.models import MetricRow
from nexus.database.repository import StorageStats
from nexus.services.background_task import BackgroundTask
from nexus.ui import theme
from nexus.ui.base import BasePage
from nexus.ui.widgets.charts import TimeSeriesChart
from nexus.ui.widgets.common import (
    Badge,
    Banner,
    Card,
    EmptyState,
    PageScroll,
    SectionHeader,
    StatsRow,
    StatTile,
)
from nexus.ui.widgets.table import Column, RecordsModel, configure_table
from nexus.utils import formatting

RANGES: tuple[tuple[str, int], ...] = (
    ("Last hour", 3_600),
    ("Last 6 hours", 21_600),
    ("Last 24 hours", 86_400),
    ("Last 7 days", 604_800),
    ("Last 30 days", 2_592_000),
)


@dataclass(frozen=True, slots=True)
class HistoryLoad:
    rows: tuple[MetricRow, ...]
    stats: StorageStats
    start: float
    end: float
    bucket_seconds: int


class HistoryPage(BasePage):
    title = "Performance History"
    subtitle = "Locally stored time-series measurements"

    def __init__(self, context) -> None:
        super().__init__(context)
        palette = theme.current_palette()
        self._task: BackgroundTask | None = None
        self._loaded = False
        self._rows: tuple[MetricRow, ...] = ()
        self._stats: StorageStats | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = PageScroll()
        root.addWidget(scroll)
        content = scroll.content_layout

        self.banner = Banner(
            "History recording is turned off in Settings. Only previously stored data is shown.",
            level="warning",
        )
        self.banner.setVisible(not self.context.settings.current.store_history)
        content.addWidget(self.banner)

        controls = Card("Range")
        controls_row = QHBoxLayout()
        controls_row.setSpacing(10)
        label = QLabel("Show")
        label.setObjectName("muted")
        controls_row.addWidget(label)
        self.range_box = QComboBox()
        for title, _seconds in RANGES:
            self.range_box.addItem(title)
        self.range_box.setCurrentIndex(2)
        self.range_box.setMinimumWidth(150)
        controls_row.addWidget(self.range_box)
        controls_row.addStretch(1)
        self.storage_badge = Badge("Loading…", "neutral")
        controls_row.addWidget(self.storage_badge)
        self.refresh_button = QPushButton("Refresh")
        controls_row.addWidget(self.refresh_button)
        controls.body.addLayout(controls_row)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.progress.setFixedHeight(4)
        controls.body.addWidget(self.progress)
        self.storage_label = QLabel("Reading local database…")
        self.storage_label.setObjectName("faint")
        self.storage_label.setWordWrap(True)
        controls.body.addWidget(self.storage_label)
        content.addWidget(controls)

        tiles = QHBoxLayout()
        tiles.setSpacing(12)
        self.points_tile = StatTile("Buckets", "—", "Aggregated intervals")
        self.cpu_tile = StatTile("CPU average", "—", "Across the range")
        self.memory_tile = StatTile("Memory average", "—", "Across the range")
        self.gpu_tile = StatTile("GPU average", "—", "Across the range")
        self.score_tile = StatTile("Health average", "—", "When recorded")
        for tile in (
            self.points_tile,
            self.cpu_tile,
            self.memory_tile,
            self.gpu_tile,
            self.score_tile,
        ):
            tiles.addWidget(tile, 1)
        content.addLayout(tiles)

        chart_card = Card("Recorded trends")
        chart_header = SectionHeader(
            "Averages per interval",
            "Charts show stored averages; gaps mean no sample was recorded.",
        )
        self.range_label = QLabel("")
        self.range_label.setObjectName("faint")
        chart_header.add_action(self.range_label)
        chart_card.body.addWidget(chart_header)
        self.chart = TimeSeriesChart(
            [
                ("CPU", palette.accent),
                ("Memory", palette.warning),
                ("GPU", palette.success),
                ("Health", "#8B5CF6"),
            ],
            max_points=260,
            y_max=100,
            height=270,
        )
        chart_card.body.addWidget(self.chart)
        content.addWidget(chart_card)

        table_card = Card()
        table_header = SectionHeader(
            "Lowest health intervals",
            "Intervals where the recorded explainable score was lowest.",
        )
        self.table_badge = Badge("—", "neutral")
        table_header.add_action(self.table_badge)
        table_card.body.addWidget(table_header)
        self.model = RecordsModel(
            [
                Column(
                    "Interval start",
                    lambda r: r.ts,
                    formatter=formatting.format_timestamp,
                    width=170,
                ),
                Column(
                    "Health score",
                    lambda r: r.score,
                    formatter=lambda v: "—" if v is None else f"{v:.0f}",
                    align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    width=110,
                ),
                Column(
                    "CPU",
                    lambda r: r.cpu_percent,
                    formatter=formatting.format_percent,
                    align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    width=90,
                ),
                Column(
                    "Memory",
                    lambda r: r.memory_percent,
                    formatter=formatting.format_percent,
                    align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    width=90,
                ),
                Column(
                    "GPU",
                    lambda r: r.gpu_percent,
                    formatter=formatting.format_percent,
                    align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    width=90,
                ),
                Column(
                    "Download",
                    lambda r: r.net_down_bps,
                    formatter=formatting.format_rate,
                    align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                ),
            ]
        )
        self.table = QTableView()
        configure_table(self.table, self.model)
        self.table.setMinimumHeight(240)
        table_card.body.addWidget(self.table)
        content.addWidget(table_card)

        self.empty = EmptyState(
            "No recorded history yet",
            "NEXUS writes one aggregated sample every monitoring interval while history storage "
            "is enabled. Leave it running for a little while, then refresh this page.",
            icon_name="history",
        )
        self.empty.setVisible(False)
        content.addWidget(self.empty)
        content.addStretch(1)

        self.range_box.currentIndexChanged.connect(lambda _index: self._load())
        self.refresh_button.clicked.connect(self._load)
        self.context.history.errorOccurred.connect(self._on_history_error)

    @staticmethod
    def _page_layout(root):
        # PageScroll is a QScrollArea; the page itself needs a zero-margin layout.
        from PySide6.QtWidgets import QVBoxLayout

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(root)
        return layout

    def __init_subclass__(cls, **kwargs):  # pragma: no cover - guard against misuse
        super().__init_subclass__(**kwargs)

    # The base page builds its own layout, so install ours lazily.
    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)

    def on_activated(self) -> None:
        if not self._loaded:
            self._load()
        elif not (self._task is not None and self._task.running):
            self._load(silent=True)

    def refresh_now(self) -> None:
        self._load()

    def refresh_theme(self) -> None:
        self.chart.apply_theme()
        self.banner.setVisible(not self.context.settings.current.store_history)

    def _on_history_error(self, message: str) -> None:
        window = self.window()
        if hasattr(window, "show_toast"):
            window.show_toast(message, "error")

    # -- loading ------------------------------------------------------------
    def _load(self, *, silent: bool = False) -> None:
        if self._task is not None and self._task.running:
            return
        index = max(0, self.range_box.currentIndex())
        seconds = RANGES[index][1]
        bucket = max(30, seconds // 240)
        end = time.time()
        start = end - seconds
        repository = self.context.repository

        def work() -> HistoryLoad:
            rows = repository.aggregate(start, end, bucket)
            return HistoryLoad(
                rows=tuple(rows),
                stats=repository.storage_stats(),
                start=start,
                end=end,
                bucket_seconds=bucket,
            )

        if not silent:
            self.progress.setVisible(True)
            self.refresh_button.setEnabled(False)
        self._task = BackgroundTask(work, parent=self)
        self._task.finished.connect(self._on_loaded)
        self._task.failed.connect(self._on_load_failed)
        self._task.start()

    def _on_load_failed(self, message: str) -> None:
        self.progress.setVisible(False)
        self.refresh_button.setEnabled(True)
        self.storage_badge.setText("Read failed")
        self.storage_badge.set_level("warning")
        self.storage_label.setText(f"History could not be read: {message}")
        window = self.window()
        if hasattr(window, "show_toast"):
            window.show_toast("Performance history could not be read.", "error")

    def _on_loaded(self, result: HistoryLoad) -> None:
        self._loaded = True
        self.progress.setVisible(False)
        self.refresh_button.setEnabled(True)
        self._rows = result.rows
        self._stats = result.stats
        self._render(result)

    def _render(self, result: HistoryLoad) -> None:
        rows = result.rows
        self.range_label.setText(
            f"{formatting.format_timestamp(result.start)} → {formatting.format_timestamp(result.end)}"
        )
        stats = result.stats
        self.storage_badge.setText(f"{stats.rows:,} stored rows")
        self.storage_badge.set_level("success" if stats.rows else "neutral")
        size = formatting.format_bytes(stats.file_size_bytes)
        oldest = (
            formatting.format_timestamp(stats.oldest_ts) if stats.oldest_ts else "no data"
        )
        newest = (
            formatting.format_timestamp(stats.newest_ts) if stats.newest_ts else "no data"
        )
        retention = self.context.settings.current.retention_days
        enabled = "enabled" if self.context.settings.current.store_history else "disabled"
        self.storage_label.setText(
            f"Database: {size} · {stats.rows:,} rows · retention {retention} days ({enabled}) "
            f"· oldest {oldest} · newest {newest}"
        )
        self.banner.setVisible(not self.context.settings.current.store_history)

        self.points_tile.set_value(str(len(rows)), f"{result.bucket_seconds}s intervals")
        self.cpu_tile.set_value(
            formatting.format_percent(_mean(row.cpu_percent for row in rows)), "Across the range"
        )
        self.memory_tile.set_value(
            formatting.format_percent(_mean(row.memory_percent for row in rows)), "Across the range"
        )
        self.gpu_tile.set_value(
            formatting.format_percent(_mean(row.gpu_percent for row in rows)), "Across the range"
        )
        self.score_tile.set_value(
            _score_text(_mean(row.score for row in rows)), "When recorded"
        )

        if not rows:
            self.chart.clear()
            self.model.set_records([])
            self.empty.setVisible(True)
            self.table_badge.setText("No data")
            self.table_badge.set_level("neutral")
            return
        self.empty.setVisible(False)
        self.chart.set_values(
            [
                (
                    row.ts,
                    {
                        "CPU": row.cpu_percent,
                        "Memory": row.memory_percent,
                        "GPU": row.gpu_percent,
                        "Health": row.score,
                    },
                )
                for row in rows
            ]
        )
        scored = [row for row in rows if row.score is not None]
        scored.sort(key=lambda row: row.score or 0)
        lowest = scored[:12]
        self.model.set_records(lowest)
        self.table_badge.setText(
            f"{len(scored)} scored intervals" if scored else "No scores recorded"
        )
        self.table_badge.set_level("info" if scored else "neutral")


def _mean(values) -> float | None:
    clean = [float(value) for value in values if value is not None]
    return sum(clean) / len(clean) if clean else None


def _score_text(value: float | None) -> str:
    return "—" if value is None else f"{value:.0f}/100"
