"""Explainable, deterministic performance-health scoring.

The score is *not* a benchmark of raw computer speed. It estimates how much
resource pressure the machine is under right now (and briefly before), using
only metrics NEXUS can actually measure. Every component is a documented,
piecewise-linear mapping with fixed anchors, so results are reproducible and
unit-testable.

Missing optional sensors never reduce the score: unavailable components are
excluded and the weights of available components are renormalised. The share
of total weight that was measurable is reported as ``coverage``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Higher anchor values mean better health.
_CPU_ANCHORS: tuple[tuple[float, float], ...] = (
    (0.0, 100.0),
    (40.0, 100.0),
    (70.0, 78.0),
    (90.0, 45.0),
    (100.0, 20.0),
)
_MEMORY_ANCHORS: tuple[tuple[float, float], ...] = (
    (0.0, 100.0),
    (50.0, 100.0),
    (75.0, 80.0),
    (90.0, 45.0),
    (100.0, 15.0),
)
# Storage uses *free* percentage, so higher is better directly.
_STORAGE_ANCHORS: tuple[tuple[float, float], ...] = (
    (0.0, 0.0),
    (5.0, 30.0),
    (10.0, 60.0),
    (15.0, 80.0),
    (25.0, 100.0),
    (100.0, 100.0),
)
_DISK_ACTIVITY_ANCHORS: tuple[tuple[float, float], ...] = (
    (0.0, 100.0),
    (50.0, 95.0),
    (80.0, 75.0),
    (100.0, 45.0),
)

_WEIGHTS = {"cpu": 0.30, "memory": 0.32, "storage": 0.23, "disk": 0.15}

METHODOLOGY: tuple[str, ...] = (
    "CPU pressure (30%): 100 until 40% sustained utilization, declining to 20 at 100%.",
    "Memory pressure (32%): 100 until 50% used, declining to 15 at 100% used.",
    "Storage headroom (23%): based on the fullest volume's free space (60 at 10% free, 30 at 5%).",
    "Disk pressure (15%): based on disk busy time when the platform exposes it.",
    "Unavailable components are excluded and remaining weights are renormalised.",
    "The score estimates current resource pressure and system health; it is not a speed benchmark.",
)


@dataclass(frozen=True, slots=True)
class ComponentScore:
    key: str
    label: str
    score: float | None
    weight: float
    detail: str
    available: bool = True


@dataclass(frozen=True, slots=True)
class ScoreInput:
    cpu_percent: float | None = None
    memory_percent: float | None = None
    storage_free_percent: float | None = None
    disk_activity_percent: float | None = None

    @classmethod
    def from_snapshot(
        cls,
        snapshot,
        *,
        sustained_cpu: float | None = None,
        sustained_memory: float | None = None,
    ) -> ScoreInput:
        """Build scoring input from a metrics snapshot.

        Sustained values use a short rolling average when available, because
        instantaneous readings are noisy.
        """
        memory_percent = (
            sustained_memory
            if sustained_memory is not None
            else (snapshot.memory.percent if snapshot.memory else None)
        )
        partitions = snapshot.disk.partitions if snapshot.disk else ()
        free_percent = None
        if partitions:
            # The fullest volume determines storage headroom.
            free_percent = min(
                100.0 * p.free_bytes / p.total_bytes for p in partitions if p.total_bytes > 0
            )
        cpu = sustained_cpu if sustained_cpu is not None else (
            snapshot.cpu.utilization_percent if snapshot.cpu else None
        )
        return cls(
            cpu_percent=cpu,
            memory_percent=memory_percent,
            storage_free_percent=free_percent,
            disk_activity_percent=snapshot.disk.activity_percent if snapshot.disk else None,
        )


@dataclass(frozen=True, slots=True)
class ScoreReport:
    total: int
    grade: str
    components: tuple[ComponentScore, ...]
    coverage: float
    confidence: str
    summary: str
    methodology: tuple[str, ...] = field(default=METHODOLOGY)


def interpolate(value: float, anchors: tuple[tuple[float, float], ...]) -> float:
    """Piecewise-linear interpolation over ascending anchors, clamped at ends."""
    points = sorted(anchors)
    if value <= points[0][0]:
        return points[0][1]
    if value >= points[-1][0]:
        return points[-1][1]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 <= value <= x1:
            if x1 == x0:
                return y1
            ratio = (value - x0) / (x1 - x0)
            return y0 + ratio * (y1 - y0)
    return points[-1][1]


def cpu_score(percent: float) -> float:
    return interpolate(max(0.0, min(100.0, percent)), _CPU_ANCHORS)


def memory_score(percent: float) -> float:
    return interpolate(max(0.0, min(100.0, percent)), _MEMORY_ANCHORS)


def storage_score(free_percent: float) -> float:
    return interpolate(max(0.0, min(100.0, free_percent)), _STORAGE_ANCHORS)


def disk_score(activity_percent: float) -> float:
    return interpolate(max(0.0, min(100.0, activity_percent)), _DISK_ACTIVITY_ANCHORS)


def grade_for(total: float) -> str:
    if total >= 85:
        return "Excellent"
    if total >= 70:
        return "Good"
    if total >= 50:
        return "Fair"
    return "Under pressure"


def confidence_for(coverage: float) -> str:
    if coverage >= 0.85:
        return "High"
    if coverage >= 0.55:
        return "Medium"
    return "Low"


def compute_score(data: ScoreInput) -> ScoreReport:
    components: list[ComponentScore] = []

    if data.cpu_percent is not None:
        components.append(
            ComponentScore(
                "cpu",
                "CPU pressure",
                round(cpu_score(data.cpu_percent), 1),
                _WEIGHTS["cpu"],
                f"CPU at {data.cpu_percent:.1f}% utilization.",
            )
        )
    else:
        components.append(
            ComponentScore("cpu", "CPU pressure", None, _WEIGHTS["cpu"], "CPU data unavailable.", False)
        )

    if data.memory_percent is not None:
        components.append(
            ComponentScore(
                "memory",
                "Memory pressure",
                round(memory_score(data.memory_percent), 1),
                _WEIGHTS["memory"],
                f"{data.memory_percent:.1f}% of physical memory in use.",
            )
        )
    else:
        components.append(
            ComponentScore(
                "memory", "Memory pressure", None, _WEIGHTS["memory"], "Memory data unavailable.", False
            )
        )

    if data.storage_free_percent is not None:
        components.append(
            ComponentScore(
                "storage",
                "Storage headroom",
                round(storage_score(data.storage_free_percent), 1),
                _WEIGHTS["storage"],
                f"Fullest volume has {data.storage_free_percent:.1f}% free.",
            )
        )
    else:
        components.append(
            ComponentScore(
                "storage",
                "Storage headroom",
                None,
                _WEIGHTS["storage"],
                "Volume capacity unavailable.",
                False,
            )
        )

    if data.disk_activity_percent is not None:
        components.append(
            ComponentScore(
                "disk",
                "Disk pressure",
                round(disk_score(data.disk_activity_percent), 1),
                _WEIGHTS["disk"],
                f"Disk busy {data.disk_activity_percent:.0f}% of the interval.",
            )
        )
    else:
        components.append(
            ComponentScore(
                "disk",
                "Disk pressure",
                None,
                _WEIGHTS["disk"],
                "Disk busy-time counter not exposed.",
                False,
            )
        )

    available_weight = sum(c.weight for c in components if c.available)
    total_weight = sum(c.weight for c in components)
    coverage = available_weight / total_weight if total_weight else 0.0
    if available_weight <= 0:
        return ScoreReport(
            total=0,
            grade="Unavailable",
            components=tuple(components),
            coverage=0.0,
            confidence="Low",
            summary="Not enough metrics are available to estimate system health.",
        )

    weighted = sum((c.score or 0.0) * c.weight for c in components if c.available)
    total = max(0, min(100, round(weighted / available_weight)))
    low_parts = [c for c in components if c.available and (c.score or 0) < 60]
    if low_parts:
        summary = "Pressure detected in " + ", ".join(c.label.lower() for c in low_parts) + "."
    elif total >= 85:
        summary = "No meaningful resource pressure detected."
    else:
        summary = "System resources are within reasonable operating ranges."

    return ScoreReport(
        total=total,
        grade=grade_for(total),
        components=tuple(components),
        coverage=round(coverage, 3),
        confidence=confidence_for(coverage),
        summary=summary,
    )
