"""Reports: preview and export measured data in HTML, JSON or CSV."""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from nexus.core.metrics import Snapshot
from nexus.core.process_manager import top_processes
from nexus.core.recommendations import RecommendationContext, RecommendationEngine
from nexus.core.scoring import ScoreInput, compute_score
from nexus.database.models import MetricRow
from nexus.services.background_task import BackgroundTask
from nexus.services.reporting_service import (
    ReportData,
    build_report,
    render_csv,
    render_html,
    render_json,
    suggested_filename,
)
from nexus.ui import theme
from nexus.ui.base import BasePage
from nexus.ui.widgets.common import Badge, Banner, Card, PageScroll, SectionHeader, StatsRow
from nexus.utils import formatting

RANGES: tuple[tuple[str, int], ...] = (
    ("Last hour", 3_600),
    ("Last 6 hours", 21_600),
    ("Last 24 hours", 86_400),
    ("Last 7 days", 604_800),
)
FORMATS = ("HTML", "JSON", "CSV")


class ReportsPage(BasePage):
    title = "Reports"
    subtitle = "Preview and export a summary of measured data"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._task: BackgroundTask | None = None
        self._report: ReportData | None = None
        self._rows: tuple[MetricRow, ...] = ()
        self._engine = RecommendationEngine()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = PageScroll()
        root.addWidget(scroll)
        content = scroll.content_layout

        content.addWidget(
            Banner(
                "Reports contain only measurements NEXUS actually collected. Missing sensors are "
                "listed as unavailable rather than estimated, and nothing is uploaded.",
                level="info",
                icon_name="info",
            )
        )

        options = Card("Report options")
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(_label("Period"))
        self.range_box = QComboBox()
        for title, _seconds in RANGES:
            self.range_box.addItem(title)
        self.range_box.setCurrentIndex(2)
        self.range_box.setMinimumWidth(140)
        row.addWidget(self.range_box)

        row.addSpacing(10)
        row.addWidget(_label("Format"))
        self.format_box = QComboBox()
        self.format_box.addItems(FORMATS)
        self.format_box.setMinimumWidth(100)
        row.addWidget(self.format_box)

        self.hostname_check = QCheckBox("Include computer name")
        self.hostname_check.setToolTip(
            "Off by default so an exported report does not identify this machine."
        )
        row.addWidget(self.hostname_check)
        row.addStretch(1)
        self.generate_button = QPushButton("Generate preview")
        self.generate_button.setObjectName("primary")
        row.addWidget(self.generate_button)
        self.export_button = QPushButton("Export…")
        self.export_button.setEnabled(False)
        row.addWidget(self.export_button)
        options.body.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.progress.setFixedHeight(4)
        options.body.addWidget(self.progress)
        self.status_label = QLabel("No preview generated yet.")
        self.status_label.setObjectName("faint")
        self.status_label.setWordWrap(True)
        options.body.addWidget(self.status_label)
        content.addWidget(options)

        summary = Card("Report summary")
        self.summary_grid = StatsRow(
            ["Period", "Stored samples", "Health score", "Recommendations"], columns=4
        )
        summary.body.addWidget(self.summary_grid)
        self.coverage_badge = Badge("Coverage —", "neutral")
        summary.add_header_widget(self.coverage_badge)
        content.addWidget(summary)

        preview_card = Card()
        header = SectionHeader(
            "Preview",
            "This is exactly what will be written to disk.",
        )
        self.preview_badge = Badge("—", "neutral")
        header.add_action(self.preview_badge)
        preview_card.body.addWidget(header)
        self.preview = QTextBrowser()
        self.preview.setOpenExternalLinks(False)
        self.preview.setMinimumHeight(430)
        preview_card.body.addWidget(self.preview)
        content.addWidget(preview_card)
        content.addStretch(1)

        self.generate_button.clicked.connect(self._generate)
        self.export_button.clicked.connect(self._export)
        self.format_box.currentIndexChanged.connect(lambda _index: self._render_preview())
        self.range_box.currentIndexChanged.connect(self._invalidate)
        self.hostname_check.toggled.connect(self._invalidate)

    # -- lifecycle ----------------------------------------------------------
    def on_activated(self) -> None:
        if self._report is None and not (self._task is not None and self._task.running):
            self._generate()

    def refresh_now(self) -> None:
        self._generate()

    def refresh_theme(self) -> None:
        self._render_preview()

    def on_snapshot(self, snapshot: Snapshot) -> None:
        # Preview is generated on demand; only freshness is tracked here.
        pass

    def _invalidate(self, *_args) -> None:
        self._report = None
        self._rows = ()
        self.export_button.setEnabled(False)
        self.status_label.setText("Options changed — generate a new preview.")
        self.preview_badge.setText("Stale")
        self.preview_badge.set_level("warning")

    # -- generation ---------------------------------------------------------
    def _generate(self) -> None:
        if self._task is not None and self._task.running:
            return
        seconds = RANGES[max(0, self.range_box.currentIndex())][1]
        end = time.time()
        start = end - seconds
        bucket = max(30, seconds // 300)
        repository = self.context.repository

        def work() -> tuple[MetricRow, ...]:
            return tuple(repository.aggregate(start, end, bucket))

        self.progress.setVisible(True)
        self.generate_button.setEnabled(False)
        self.status_label.setText("Reading stored measurements…")
        self._task = BackgroundTask(work, parent=self)
        self._task.finished.connect(self._on_rows_loaded)
        self._task.failed.connect(self._on_failed)
        self._task.start()

    def _on_failed(self, message: str) -> None:
        self.progress.setVisible(False)
        self.generate_button.setEnabled(True)
        self.status_label.setText(f"Report could not be generated: {message}")
        self.preview_badge.setText("Failed")
        self.preview_badge.set_level("warning")

    def _on_rows_loaded(self, rows: tuple[MetricRow, ...]) -> None:
        self.progress.setVisible(False)
        self.generate_button.setEnabled(True)
        self._rows = rows
        snapshot = self.context.monitoring.latest
        score = None
        recommendations: list = []
        if snapshot is not None:
            try:
                score = compute_score(ScoreInput.from_snapshot(snapshot))
            except Exception:
                score = None
            try:
                processes = self.context.processes.latest
                cpu_leaders = top_processes(processes, key="cpu", limit=4) if processes else []
                memory_leaders = top_processes(processes, key="memory", limit=4) if processes else []
                settings = self.context.settings.current
                recommendations = self._engine.evaluate(
                    RecommendationContext(
                        snapshot=snapshot,
                        cpu_threshold_percent=settings.cpu_warning_threshold,
                        memory_threshold_percent=settings.memory_warning_threshold,
                        storage_free_threshold_percent=settings.storage_warning_threshold,
                        top_cpu_processes=tuple((p.name, p.cpu_percent) for p in cpu_leaders),
                        top_memory_processes=tuple(
                            (p.name, p.memory_rss / (1024**2)) for p in memory_leaders
                        ),
                        score=score,
                    )
                )
            except Exception:
                recommendations = []

        missing = snapshot.missing_metrics() if snapshot is not None else ["All live metrics"]
        include_hostname = self.hostname_check.isChecked()
        report = build_report(
            snapshot=snapshot,
            rows=rows,
            score=score,
            recommendations=recommendations,
            missing_metrics=missing,
            include_hostname=include_hostname,
            notes=(
                "Values are measured locally by NEXUS; unavailable sensors are listed, not estimated.",
                f"Computer name: {'included' if include_hostname else 'omitted'} in this report.",
                "The health score estimates current resource pressure, not raw hardware speed.",
            ),
        )
        self._report = report
        period = "No stored samples in the selected period"
        if rows:
            period = (
                f"{formatting.format_timestamp(rows[0].ts)} → "
                f"{formatting.format_timestamp(rows[-1].ts)}"
            )
        self.summary_grid.set_values(
            {
                "Period": period,
                "Stored samples": f"{len(rows):,}",
                "Health score": (
                    f"{report.score.get('total')}/100" if report.score else "Unavailable"
                ),
                "Recommendations": str(len(report.recommendations)),
            }
        )
        coverage = report.score.get("coverage_percent") if report.score else None
        self.coverage_badge.setText(
            f"Coverage {coverage:.0f}%" if isinstance(coverage, (int, float)) else "Coverage —"
        )
        self.coverage_badge.set_level("info" if report.score else "neutral")
        self.export_button.setEnabled(True)
        self.status_label.setText(
            f"Preview generated for {len(rows):,} aggregated samples. "
            f"Version {report.app_version}."
        )
        self._render_preview()

    # -- preview / export ---------------------------------------------------
    def _render_preview(self) -> None:
        report = self._report
        if report is None:
            return
        kind = self.format_box.currentText()
        self.preview_badge.setText(kind)
        self.preview_badge.set_level("info")
        if kind == "HTML":
            self.preview.setHtml(render_html(report))
        elif kind == "JSON":
            self.preview.setPlainText(render_json(report))
        else:
            self.preview.setPlainText(render_csv(report))

    def _export(self) -> None:
        report = self._report
        if report is None:
            return
        kind = self.format_box.currentText().lower()
        extension = {"html": "html", "json": "json", "csv": "csv"}[kind]
        settings = self.context.settings.current
        default_dir = Path(settings.export_dir)
        try:
            default_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            default_dir = Path.home()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export report",
            str(default_dir / suggested_filename(extension)),
            f"{kind.upper()} files (*.{extension})",
        )
        if not path:
            return
        content = (
            render_html(report)
            if kind == "html"
            else render_json(report)
            if kind == "json"
            else render_csv(report)
        )
        try:
            Path(path).write_text(
                content, encoding="utf-8-sig" if kind == "csv" else "utf-8"
            )
        except OSError as exc:
            self.status_label.setText(f"Export failed: {exc}")
            return
        self.status_label.setText(f"Exported {kind.upper()} to {path}")
        window = self.window()
        if hasattr(window, "show_toast"):
            window.show_toast(f"Report exported to {path}", "success")


def _label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("muted")
    return label
