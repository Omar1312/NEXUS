"""Rule-based, fully offline optimization recommendations.

Each finding names a unique rule, the observed evidence, and one or more
non-destructive actions. NEXUS never changes the system on its own: actions
navigate the user to the relevant screen or Windows settings.

High utilization is intentionally *not* treated as a defect. The rules describe
what was observed and what the user may choose to review.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence

from nexus.platforms.selection import platform_id

from nexus.core.metrics import Snapshot
from nexus.core.scoring import ScoreReport


class Severity(str, Enum):
    INFO = "info"
    NOTICE = "notice"
    WARNING = "warning"
    CRITICAL = "critical"

    @property
    def label(self) -> str:
        return {
            "info": "Info",
            "notice": "Review",
            "warning": "Warning",
            "critical": "Critical",
        }[self.value]


@dataclass(frozen=True, slots=True)
class RecommendationAction:
    label: str
    kind: str  # "navigate" | "open_uri" | "none"
    target: str = ""


@dataclass(frozen=True, slots=True)
class Recommendation:
    rule_id: str
    title: str
    severity: Severity
    summary: str
    explanation: str
    evidence: tuple[str, ...] = ()
    actions: tuple[RecommendationAction, ...] = ()
    confidence: str = "Measured"


@dataclass(frozen=True, slots=True)
class RecommendationContext:
    snapshot: Snapshot | None
    sustained_cpu_percent: float | None = None
    sustained_memory_percent: float | None = None
    cpu_threshold_percent: float = 85.0
    memory_threshold_percent: float = 85.0
    storage_free_threshold_percent: float = 10.0
    startup_entry_count: int | None = None
    optional_startup_count: int | None = None
    top_cpu_processes: tuple[tuple[str, float], ...] = ()
    top_memory_processes: tuple[tuple[str, float], ...] = ()
    score: ScoreReport | None = None
    min_observation_seconds: float = 0.0


class RecommendationEngine:
    """Evaluates an ordered list of independent rules."""

    def __init__(self) -> None:
        self._rules = (
            self._rule_cpu_pressure,
            self._rule_memory_pressure,
            self._rule_low_storage,
            self._rule_startup_review,
            self._rule_disk_pressure,
            self._rule_score_summary,
        )

    def evaluate(self, context: RecommendationContext) -> list[Recommendation]:
        findings: list[Recommendation] = []
        for rule in self._rules:
            try:
                result = rule(context)
            except Exception:
                # A failing rule must never break the Optimization Center.
                result = []
            if result:
                findings.extend(result)
        order = {Severity.CRITICAL: 0, Severity.WARNING: 1, Severity.NOTICE: 2, Severity.INFO: 3}
        findings.sort(key=lambda f: (order[f.severity], f.title))
        return findings

    # -- rules --------------------------------------------------------------
    def _rule_cpu_pressure(self, ctx: RecommendationContext) -> list[Recommendation]:
        observed = ctx.sustained_cpu_percent
        if observed is None or ctx.snapshot is None:
            return []
        if observed < ctx.cpu_threshold_percent:
            return []
        severity = Severity.CRITICAL if observed >= 96 else Severity.WARNING
        top = ctx.top_cpu_processes[:4]
        evidence = [f"Sustained CPU utilization: {observed:.1f}% (threshold {ctx.cpu_threshold_percent:.1f}%)."]
        evidence.extend(f"{name} uses {value:.1f}% CPU" for name, value in top)
        if ctx.snapshot.cpu and ctx.snapshot.cpu.logical_cores:
            evidence.append(f"Logical processors: {ctx.snapshot.cpu.logical_cores}")
        detail = (
            "High CPU utilization means the processor is busy; it is not automatically a fault. "
            "It only matters if the machine feels slow or the workload is unexpected. "
            "Review the listed processes and close work you no longer need."
        )
        return [
            Recommendation(
                rule_id="PERF-CPU-001",
                title="Sustained CPU utilization is high",
                severity=severity,
                summary=f"CPU has averaged {observed:.0f}% recently.",
                explanation=detail,
                evidence=tuple(evidence),
                actions=(
                    RecommendationAction("Review processes", "navigate", "processes"),
                    RecommendationAction("View CPU sensors", "navigate", "hardware"),
                ),
            )
        ]

    def _rule_memory_pressure(self, ctx: RecommendationContext) -> list[Recommendation]:
        observed = ctx.sustained_memory_percent
        if observed is None or ctx.snapshot is None or ctx.snapshot.memory is None:
            return []
        if observed < ctx.memory_threshold_percent:
            return []
        severity = Severity.CRITICAL if observed >= 96 else Severity.WARNING
        memory = ctx.snapshot.memory
        free_gib = memory.available_bytes / (1024**3)
        evidence = [
            f"Sustained memory utilization: {observed:.1f}% (threshold {ctx.memory_threshold_percent:.1f}%).",
            f"Available physical memory: {free_gib:.2f} GiB of {memory.total_bytes / (1024**3):.2f} GiB.",
        ]
        evidence.extend(f"{name} uses {value:.0f} MiB" for name, value in ctx.top_memory_processes[:4])
        return [
            Recommendation(
                rule_id="PERF-MEM-001",
                title="Physical memory is under sustained pressure",
                severity=severity,
                summary=f"Memory has averaged {observed:.0f}% used.",
                explanation=(
                    "The operating system uses free memory for caching, so a high number alone does not prove a "
                    "problem. Sustained pressure with little available memory can cause paging and "
                    "stutter. Closing memory-heavy applications you are not using is the safest remedy."
                ),
                evidence=tuple(evidence),
                actions=(
                    RecommendationAction("Review processes", "navigate", "processes"),
                    RecommendationAction("Open Memory details", "navigate", "hardware"),
                ),
            )
        ]

    def _rule_low_storage(self, ctx: RecommendationContext) -> list[Recommendation]:
        if ctx.snapshot is None or ctx.snapshot.disk is None:
            return []
        low: list[str] = []
        worst: float | None = None
        for partition in ctx.snapshot.disk.partitions:
            if partition.total_bytes <= 0:
                continue
            free_percent = 100.0 * partition.free_bytes / partition.total_bytes
            worst = free_percent if worst is None else min(worst, free_percent)
            if free_percent < ctx.storage_free_threshold_percent:
                low.append(
                    f"{partition.mountpoint} has {partition.free_bytes / (1024**3):.1f} GiB free "
                    f"({free_percent:.1f}%)"
                )
        if not low:
            return []
        severity = Severity.WARNING if (worst or 0) >= 5 else Severity.CRITICAL
        return [
            Recommendation(
                rule_id="STORAGE-FREE-001",
                title="A volume is running low on free space",
                severity=severity,
                summary="Free space is below the configured warning threshold.",
                explanation=(
                    "Low free space can prevent system updates, slow down temporary-file activity "
                    "and reduce reliability. Reviewing the largest folders is safe and reversible."
                ),
                evidence=tuple(low),
                actions=(
                    RecommendationAction("Analyze storage", "navigate", "storage"),
                    RecommendationAction(
                        "Open storage settings",
                        "open_uri",
                        "x-apple.systempreferences:com.apple.settings.Storage" if platform_id() == "macos" else "ms-settings:storagesense"
                    ),
                ),
            )
        ]

    def _rule_startup_review(self, ctx: RecommendationContext) -> list[Recommendation]:
        if not ctx.startup_entry_count:
            return []
        if ctx.startup_entry_count < 10:
            return []
        optional = ctx.optional_startup_count or 0
        return [
            Recommendation(
                rule_id="STARTUP-REVIEW-001",
                title="Startup configuration is worth reviewing",
                severity=Severity.NOTICE if ctx.startup_entry_count < 20 else Severity.WARNING,
                summary=f"{ctx.startup_entry_count} startup entries detected.",
                explanation=(
                    "Startup entries can lengthen sign-in time, but NEXUS does not measure per-entry "
                    "boot impact and does not disable anything automatically. Review the list and "
                    "change only entries you recognise in your operating-system settings."
                ),
                evidence=(
                    f"{ctx.startup_entry_count} registered startup entries.",
                    f"{optional} entries are marked optional or third-party where identifiable.",
                    "Per-entry startup impact is not measured; no estimate is fabricated.",
                ),
                actions=(
                    RecommendationAction("Review startup apps", "navigate", "startup"),
                    RecommendationAction(
                        "Open Login Items" if platform_id() == "macos" else "Open Windows Startup Apps",
                        "open_uri",
                        "x-apple.systempreferences:com.apple.LoginItems-Settings.extension" if platform_id() == "macos" else "ms-settings:startupapps"
                    ),
                ),
            )
        ]

    def _rule_disk_pressure(self, ctx: RecommendationContext) -> list[Recommendation]:
        if ctx.snapshot is None or ctx.snapshot.disk is None:
            return []
        activity = ctx.snapshot.disk.activity_percent
        if activity is None or activity < 90.0:
            return []
        return [
            Recommendation(
                rule_id="PERF-DISK-001",
                title="Disk is busy for most of each interval",
                severity=Severity.NOTICE,
                summary=f"Disk activity is {activity:.0f}%.",
                explanation=(
                    "Sustained disk activity can indicate indexing, updates, antivirus scanning or an "
                    "application doing heavy I/O. Excluding NEXUS itself, check which apps are active "
                    "in the process list before changing anything."
                ),
                evidence=(f"Disk busy-time counter: {activity:.0f}%.",),
                actions=(RecommendationAction("Open processes", "navigate", "processes"),),
            )
        ]

    def _rule_score_summary(self, ctx: RecommendationContext) -> list[Recommendation]:
        if ctx.score is None or ctx.score.total <= 0 or ctx.score.total >= 50:
            return []
        available = [c for c in ctx.score.components if c.available and (c.score or 0) < 50]
        if not available:
            return []
        return [
            Recommendation(
                rule_id="HEALTH-SCORE-001",
                title="Health score is low due to measured pressure",
                severity=Severity.WARNING if ctx.score.total >= 30 else Severity.CRITICAL,
                summary=f"Estimated health score: {ctx.score.total}/100 ({ctx.score.grade}).",
                explanation=(
                    "This score reflects current resource pressure, not raw hardware speed. "
                    "The components below contributed the most pressure. Missing sensors are not "
                    "penalised."
                ),
                evidence=tuple(f"{c.label}: {c.score:.0f}/100 ({c.detail})" for c in available),
                actions=(
                    RecommendationAction("View performance history", "navigate", "history"),
                    RecommendationAction("Open settings", "navigate", "settings"),
                ),
            )
        ]


def startup_optional_count(entries: Sequence[object]) -> int:
    """Count entries that look optional without guessing their boot impact."""
    optional = 0
    for entry in entries:
        name = str(getattr(entry, "name", "")).lower()
        source = str(getattr(entry, "source", "")).lower()
        if any(token in name for token in ("update", "updater", "launcher", "helper", "tray")):
            if "windows" not in source and "microsoft" not in name:
                optional += 1
    return optional
