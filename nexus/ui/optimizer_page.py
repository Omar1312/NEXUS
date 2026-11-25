"""Optimization Center: explainable score, diagnostics and recommendations."""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from nexus.core.metrics import Snapshot, SustainedTracker
from nexus.core.process_manager import top_processes
from nexus.core.recommendations import (
    Recommendation,
    RecommendationAction,
    RecommendationContext,
    RecommendationEngine,
    Severity,
    startup_optional_count,
)
from nexus.core.scoring import METHODOLOGY, ScoreReport, compute_score, ScoreInput
from nexus.platforms.macos.startup import startup_analyzer
from nexus.services.background_task import BackgroundTask
from nexus.ui import theme
from nexus.ui.base import BasePage
from nexus.ui.widgets.common import (
    Badge,
    Banner,
    Card,
    EmptyState,
    PageScroll,
    SectionHeader,
    StatsRow,
)
from nexus.ui.widgets.score_ring import ScoreRing
from nexus.utils.windows_shell import open_uri

SEVERITY_LEVEL = {
    Severity.CRITICAL: "critical",
    Severity.WARNING: "warning",
    Severity.NOTICE: "info",
    Severity.INFO: "neutral",
}


class ComponentRow(QWidget):
    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        palette = theme.current_palette()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        top = QHBoxLayout()
        top.setSpacing(8)
        self.label = QLabel(label)
        self.label.setStyleSheet("font-weight: 600; font-size: 9.5pt;")
        self.weight = QLabel("")
        self.weight.setObjectName("faint")
        self.score = QLabel("—")
        self.score.setStyleSheet("font-weight: 600;")
        top.addWidget(self.label)
        top.addStretch(1)
        top.addWidget(self.weight)
        top.addWidget(self.score)
        layout.addLayout(top)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(5)
        layout.addWidget(self.bar)
        self.detail = QLabel("")
        self.detail.setObjectName("faint")
        self.detail.setWordWrap(True)
        layout.addWidget(self.detail)
        self._palette = palette

    def set_data(self, score: float | None, weight: float, detail: str, available: bool = True) -> None:
        palette = theme.current_palette()
        self.weight.setText(f"{weight:.0%} weight")
        if not available or score is None:
            self.score.setText("Unavailable")
            self.score.setStyleSheet(f"color: {palette.text_faint}; font-weight: 600;")
            self.bar.setValue(0)
            self.bar.setStyleSheet("")
        else:
            self.score.setText(f"{score:.0f}")
            if score >= 85:
                color = palette.success
            elif score >= 70:
                color = palette.accent
            elif score >= 50:
                color = palette.warning
            else:
                color = palette.critical
            self.score.setStyleSheet(f"color: {color}; font-weight: 600;")
            self.bar.setValue(int(score))
            self.bar.setStyleSheet(
                f"QProgressBar::chunk {{ background-color: {color}; border-radius: 2px; }}"
            )
        self.detail.setText(detail)


class RecommendationCard(Card):
    navigateRequested = Signal(str)

    def __init__(self, recommendation: Recommendation, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.recommendation = recommendation
        header = QHBoxLayout()
        header.setSpacing(8)
        level = SEVERITY_LEVEL.get(recommendation.severity, "neutral")
        badge = Badge(recommendation.severity.label, level)
        header.addWidget(badge)
        title = QLabel(recommendation.title)
        title.setStyleSheet("font-size: 11pt; font-weight: 650;")
        title.setWordWrap(True)
        header.addWidget(title, 1)
        rule = QLabel(recommendation.rule_id)
        rule.setObjectName("faint")
        header.addWidget(rule)
        self.body.addLayout(header)

        summary = QLabel(recommendation.summary)
        summary.setObjectName("muted")
        summary.setWordWrap(True)
        self.body.addWidget(summary)

        explanation = QLabel(recommendation.explanation)
        explanation.setWordWrap(True)
        explanation.setStyleSheet("font-size: 9.2pt;")
        self.body.addWidget(explanation)

        if recommendation.evidence:
            evidence_title = QLabel("Evidence")
            evidence_title.setObjectName("metricLabel")
            self.body.addWidget(evidence_title)
            for item in recommendation.evidence:
                label = QLabel(f"•  {item}")
                label.setObjectName("muted")
                label.setWordWrap(True)
                self.body.addWidget(label)

        if recommendation.actions:
            actions = QHBoxLayout()
            actions.setSpacing(8)
            for action in recommendation.actions:
                button = QPushButton(action.label)
                button.setObjectName("ghost")
                button.setCursor(Qt.CursorShape.PointingHandCursor)
                button.clicked.connect(lambda _checked=False, a=action: self._run_action(a))
                actions.addWidget(button)
            actions.addStretch(1)
            actions.addWidget(QLabel(f"Confidence: {recommendation.confidence}"))
            self.body.addLayout(actions)

    def _run_action(self, action: RecommendationAction) -> None:
        page = self.window()
        if action.kind == "navigate":
            self.navigateRequested.emit(action.target)
        elif action.kind == "open_uri":
            if not open_uri(action.target) and hasattr(page, "show_toast"):
                page.show_toast("System settings could not be opened.", "warning")


class OptimizerPage(BasePage):
    title = "Optimization Center"
    subtitle = "Measured diagnostics and explainable recommendations"

    def __init__(self, context) -> None:
        super().__init__(context)
        palette = theme.current_palette()
        self._cpu_tracker = SustainedTracker(window_seconds=20.0, min_samples=5)
        self._memory_tracker = SustainedTracker(window_seconds=20.0, min_samples=5)
        self._engine = RecommendationEngine()
        self._score: ScoreReport | None = None
        self._signature: tuple | None = None
        self._startup_count: int | None = None
        self._startup_optional: int | None = None
        self._startup_task: BackgroundTask | None = None
        self._recommendation_widgets: list[RecommendationCard] = []
        self._last_processes = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = PageScroll()
        root.addWidget(scroll)
        content = scroll.content_layout

        top_row = QHBoxLayout()
        top_row.setSpacing(14)

        score_card = Card("System health")
        score_layout = QHBoxLayout()
        score_layout.setSpacing(18)
        self.ring = ScoreRing(diameter=188)
        score_layout.addWidget(self.ring, 0, Qt.AlignmentFlag.AlignTop)
        score_text = QVBoxLayout()
        score_text.setSpacing(6)
        self.grade_label = QLabel("Waiting for data")
        self.grade_label.setStyleSheet("font-size: 13pt; font-weight: 650;")
        score_text.addWidget(self.grade_label)
        self.summary_label = QLabel(
            "The score estimates current resource pressure and system health. "
            "It is not a benchmark of computer speed."
        )
        self.summary_label.setObjectName("muted")
        self.summary_label.setWordWrap(True)
        score_text.addWidget(self.summary_label)
        badge_row = QHBoxLayout()
        badge_row.setSpacing(6)
        self.confidence_badge = Badge("Confidence —", "neutral")
        self.coverage_badge = Badge("Coverage —", "neutral")
        badge_row.addWidget(self.confidence_badge)
        badge_row.addWidget(self.coverage_badge)
        badge_row.addStretch(1)
        score_text.addLayout(badge_row)
        self.score_stats = StatsRow(["CPU pressure", "Memory pressure", "Disk activity", "Free space"], columns=2)
        score_text.addWidget(self.score_stats)
        score_text.addStretch(1)
        score_layout.addLayout(score_text, 1)
        score_card.body.addLayout(score_layout)
        top_row.addWidget(score_card, 3)

        components_card = Card("Component scores")
        components_card.body.setSpacing(12)
        self.components: dict[str, ComponentRow] = {}
        for key, label in (
            ("cpu", "CPU pressure"),
            ("memory", "Memory pressure"),
            ("storage", "Storage headroom"),
            ("disk", "Disk pressure"),
        ):
            row = ComponentRow(label)
            self.components[key] = row
            components_card.body.addWidget(row)
        self.method_button = QToolButton()
        self.method_button.setText("How is this calculated?")
        self.method_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.method_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.method_button.clicked.connect(self._toggle_methodology)
        components_card.body.addWidget(self.method_button, 0, Qt.AlignmentFlag.AlignLeft)
        self.method_label = QLabel(
            "\n".join(f"•  {line}" for line in METHODOLOGY)
        )
        self.method_label.setObjectName("muted")
        self.method_label.setWordWrap(True)
        self.method_label.setVisible(False)
        components_card.body.addWidget(self.method_label)
        components_card.body.addStretch(1)
        top_row.addWidget(components_card, 2)
        content.addLayout(top_row)

        rec_header = SectionHeader(
            "Recommendations",
            "Rules run locally from measured data. Nothing is changed without your action.",
        )
        self.rec_badge = Badge("0 findings", "neutral")
        rec_header.add_action(self.rec_badge)
        content.addWidget(rec_header)
        self.rec_container = QWidget()
        self.rec_layout = QVBoxLayout(self.rec_container)
        self.rec_layout.setContentsMargins(0, 0, 0, 0)
        self.rec_layout.setSpacing(10)
        content.addWidget(self.rec_container)

        interpretation = Banner(
            "High CPU or memory utilization is not automatically a problem; it only matters when "
            "the machine feels slow or the workload is unexpected. Thresholds are configurable in Settings.",
            level="info",
            icon_name="info",
        )
        content.addWidget(interpretation)
        content.addStretch(1)

        self.context.processes.sampleReady.connect(self._on_processes)
        latest = context.monitoring.latest
        if latest is not None:
            self.on_snapshot(latest)
        else:
            self._render_empty()
        if not context.database_persistent:
            content.insertWidget(0, Banner("History is not persisted this session: the local database could not be opened.", level="warning"))

    # -- lifecycle ----------------------------------------------------------
    def on_activated(self) -> None:
        self.context.processes.set_active(True)
        if self._startup_task is None and self._startup_count is None:
            self._startup_task = BackgroundTask(startup_analyzer().scan, parent=self)
            self._startup_task.finished.connect(self._on_startup_scanned)
            self._startup_task.failed.connect(
                lambda message: logging.getLogger(__name__).info(
                    "Startup analysis unavailable: %s", message
                )
            )
            self._startup_task.start()

    def on_deactivated(self) -> None:
        self.context.processes.set_active(False)

    def refresh_now(self) -> None:
        self.context.monitoring.refresh_now()

    def refresh_theme(self) -> None:
        for row in self.components.values():
            row.update()
        latest = self.context.monitoring.latest
        if latest is not None:
            self.on_snapshot(latest)

    def _on_startup_scanned(self, result) -> None:
        self._startup_count = len(result.entries)
        self._startup_optional = startup_optional_count(result.entries)
        latest = self.context.monitoring.latest
        if latest is not None:
            self.on_snapshot(latest)

    def _on_processes(self, processes) -> None:
        self._last_processes = processes

    # -- updates ------------------------------------------------------------
    def on_snapshot(self, snapshot: Snapshot) -> None:
        settings = self.context.settings.current
        cpu_value = snapshot.cpu.utilization_percent if snapshot.cpu else None
        memory_value = snapshot.memory.percent if snapshot.memory else None
        self._cpu_tracker.add(snapshot.timestamp, cpu_value)
        self._memory_tracker.add(snapshot.timestamp, memory_value)
        cpu_sustained = self._cpu_tracker.average()
        memory_sustained = self._memory_tracker.average()
        score_input = ScoreInput.from_snapshot(
            snapshot, sustained_cpu=cpu_sustained, sustained_memory=memory_sustained
        )
        score = compute_score(score_input)
        self._score = score

        top_cpu = top_processes(self._last_processes, key="cpu", limit=5) if self._last_processes else []
        top_memory = (
            top_processes(self._last_processes, key="memory", limit=5) if self._last_processes else []
        )
        context = RecommendationContext(
            snapshot=snapshot,
            sustained_cpu_percent=cpu_sustained,
            sustained_memory_percent=memory_sustained,
            cpu_threshold_percent=settings.cpu_warning_threshold,
            memory_threshold_percent=settings.memory_warning_threshold,
            storage_free_threshold_percent=settings.storage_warning_threshold,
            startup_entry_count=self._startup_count,
            optional_startup_count=self._startup_optional,
            top_cpu_processes=tuple((p.name, p.cpu_percent) for p in top_cpu),
            top_memory_processes=tuple((p.name, p.memory_rss / (1024**2)) for p in top_memory),
            score=score,
            min_observation_seconds=self._cpu_tracker.elapsed(),
        )
        findings = self._engine.evaluate(context)

        self._render_score(score, snapshot, cpu_sustained, memory_sustained)
        signature = tuple(
            (finding.rule_id, finding.severity.value, int((cpu_sustained or 0) // 5), int((memory_sustained or 0) // 5))
            for finding in findings
        )
        if signature != self._signature:
            self._signature = signature
            self._render_recommendations(findings)

    def _render_score(
        self,
        score: ScoreReport,
        snapshot: Snapshot,
        cpu_sustained: float | None,
        memory_sustained: float | None,
    ) -> None:
        self.ring.set_score(
            score.total if score.total > 0 else None, score.grade, animate=True
        )
        self.grade_label.setText(f"{score.grade} · {score.total}/100" if score.total else "Insufficient data")
        self.summary_label.setText(score.summary)
        self.confidence_badge.setText(f"Confidence {score.confidence}")
        self.confidence_badge.set_level(
            "success" if score.confidence == "High" else "info" if score.confidence == "Medium" else "warning"
        )
        self.coverage_badge.setText(f"Coverage {score.coverage * 100:.0f}%")
        self.coverage_badge.set_level("neutral")
        memory = snapshot.memory
        disk = snapshot.disk
        free_percent = None
        if disk and disk.partitions:
            free_percent = min(
                100.0 * p.free_bytes / p.total_bytes for p in disk.partitions if p.total_bytes
            )
        self.score_stats.set_values(
            {
                "CPU pressure": f"{cpu_sustained:.0f}%" if cpu_sustained is not None else "Collecting…",
                "Memory pressure": f"{memory_sustained:.0f}%" if memory_sustained is not None else "Collecting…",
                "Disk activity": (
                    f"{disk.activity_percent:.0f}%" if disk and disk.activity_percent is not None else "Unavailable"
                ),
                "Free space": f"{free_percent:.0f}%" if free_percent is not None else "Unavailable",
            }
        )
        for component in score.components:
            row = self.components.get(component.key)
            if row is not None:
                row.set_data(
                    component.score,
                    component.weight,
                    component.detail,
                    available=component.available,
                )
        if memory is not None:
            self.score_stats.setToolTip(
                f"Physical memory: {memory.percent:.1f}% used "
                f"({memory.available_bytes / (1024**3):.1f} GiB available)"
            )

    def _render_recommendations(self, findings: list[Recommendation]) -> None:
        while self.rec_layout.count():
            item = self.rec_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._recommendation_widgets.clear()
        if not findings:
            self.rec_layout.addWidget(
                EmptyState(
                    "No measured pressure detected",
                    "All tracked metrics are within the configured thresholds. Recommendations "
                    "appear only when sustained measurements support them.",
                    icon_name="check",
                )
            )
            self.rec_badge.setText("No findings")
            self.rec_badge.set_level("success")
            return
        self.rec_badge.setText(f"{len(findings)} finding{'s' if len(findings) != 1 else ''}")
        self.rec_badge.set_level("warning" if any(f.severity in (Severity.WARNING, Severity.CRITICAL) for f in findings) else "info")
        for finding in findings:
            card = RecommendationCard(finding)
            card.navigateRequested.connect(self.navigateRequested)
            self._recommendation_widgets.append(card)
            self.rec_layout.addWidget(card)

    def _render_empty(self) -> None:
        self._render_recommendations([])

    def _toggle_methodology(self) -> None:
        self.method_label.setVisible(not self.method_label.isVisible())
        self.method_button.setText(
            "Hide calculation details" if self.method_label.isVisible() else "How is this calculated?"
        )
