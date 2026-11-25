"""Manually started gaming monitoring sessions.

NEXUS does not measure in-game FPS, inject into games or touch anti-cheat
software. A session records the same real system metrics as the dashboard and
produces a post-session statistical report from them.
"""

from __future__ import annotations

import statistics
import time
from dataclasses import asdict, dataclass, field

from nexus.core.metrics import Snapshot


@dataclass(frozen=True, slots=True)
class GamingSample:
    ts: float
    cpu_percent: float | None = None
    gpu_percent: float | None = None
    memory_percent: float | None = None
    memory_used_bytes: int | None = None
    gpu_memory_percent: float | None = None
    gpu_temperature_c: float | None = None
    gpu_power_watts: float | None = None


@dataclass(frozen=True, slots=True)
class GamingSummary:
    duration_seconds: float
    sample_count: int
    cpu_average: float | None
    cpu_peak: float | None
    gpu_average: float | None
    gpu_peak: float | None
    memory_peak_percent: float | None
    memory_peak_bytes: int | None
    vram_peak_percent: float | None
    gpu_temperature_min: float | None
    gpu_temperature_average: float | None
    gpu_temperature_max: float | None
    gpu_power_average: float | None
    missing_metrics: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _average(values: list[float]) -> float | None:
    return round(statistics.fmean(values), 1) if values else None


def _peak(values: list[float]) -> float | None:
    return round(max(values), 1) if values else None


class GamingSessionRecorder:
    """Collects timestamped samples while a session is active."""

    def __init__(self, *, max_samples: int = 21_600) -> None:
        self._max_samples = max(60, max_samples)
        self._samples: list[GamingSample] = []
        self._started_at: float | None = None
        self._stopped_at: float | None = None

    @property
    def active(self) -> bool:
        return self._started_at is not None and self._stopped_at is None

    @property
    def started_at(self) -> float | None:
        return self._started_at

    @property
    def sample_count(self) -> int:
        return len(self._samples)

    @property
    def samples(self) -> tuple[GamingSample, ...]:
        return tuple(self._samples)

    def start(self, *, now: float | None = None) -> None:
        self._samples.clear()
        self._started_at = now if now is not None else time.time()
        self._stopped_at = None

    def stop(self, *, now: float | None = None) -> GamingSummary:
        if self._started_at is None:
            raise RuntimeError("No gaming session is active.")
        self._stopped_at = now if now is not None else time.time()
        return self.summary()

    def add_snapshot(self, snapshot: Snapshot) -> bool:
        """Record a sample if the session is active. Returns True if stored."""
        if not self.active:
            return False
        gpu = snapshot.gpus[0] if snapshot.gpus else None
        sample = GamingSample(
            ts=snapshot.timestamp,
            cpu_percent=snapshot.cpu.utilization_percent if snapshot.cpu else None,
            gpu_percent=gpu.utilization_percent if gpu else None,
            memory_percent=snapshot.memory.percent if snapshot.memory else None,
            memory_used_bytes=snapshot.memory.used_bytes if snapshot.memory else None,
            gpu_memory_percent=gpu.memory_percent if gpu else None,
            gpu_temperature_c=gpu.temperature_c if gpu else None,
            gpu_power_watts=gpu.power_watts if gpu else None,
        )
        self._samples.append(sample)
        if len(self._samples) > self._max_samples:
            # Keep a bounded history; drop the oldest at ~10% chunks to avoid churn.
            del self._samples[: max(1, self._max_samples // 10)]
        return True

    def summary(self) -> GamingSummary:
        cpu = [s.cpu_percent for s in self._samples if s.cpu_percent is not None]
        gpu = [s.gpu_percent for s in self._samples if s.gpu_percent is not None]
        memory = [s.memory_percent for s in self._samples if s.memory_percent is not None]
        memory_bytes = [s.memory_used_bytes for s in self._samples if s.memory_used_bytes is not None]
        vram = [s.gpu_memory_percent for s in self._samples if s.gpu_memory_percent is not None]
        temperatures = [s.gpu_temperature_c for s in self._samples if s.gpu_temperature_c is not None]
        power = [s.gpu_power_watts for s in self._samples if s.gpu_power_watts is not None]
        peak_memory_bytes: int | None = max(memory_bytes) if memory_bytes else None
        missing: list[str] = []
        if not cpu:
            missing.append("CPU utilization")
        if not gpu:
            missing.append("GPU utilization")
        if not temperatures:
            missing.append("GPU temperature")
        if not power:
            missing.append("GPU power")
        if not vram:
            missing.append("GPU memory")
        duration = 0.0
        if self._started_at is not None:
            end = self._stopped_at if self._stopped_at is not None else time.time()
            duration = max(0.0, end - self._started_at)
        return GamingSummary(
            duration_seconds=round(duration, 1),
            sample_count=len(self._samples),
            cpu_average=_average(cpu),
            cpu_peak=_peak(cpu),
            gpu_average=_average(gpu),
            gpu_peak=_peak(gpu),
            memory_peak_percent=_peak(memory),
            memory_peak_bytes=peak_memory_bytes,
            vram_peak_percent=_peak(vram),
            gpu_temperature_min=round(min(temperatures), 1) if temperatures else None,
            gpu_temperature_average=_average(temperatures),
            gpu_temperature_max=_peak(temperatures),
            gpu_power_average=_average(power),
            missing_metrics=tuple(missing),
        )

    def samples_payload(self, *, limit: int = 3600) -> list[dict[str, float | None]]:
        """Compact sample list for persistence (bounded to keep the DB small)."""
        samples = self._samples[-limit:] if limit > 0 else self._samples
        return [asdict(sample) for sample in samples]

    def reset(self) -> None:
        self._samples.clear()
        self._started_at = None
        self._stopped_at = None
