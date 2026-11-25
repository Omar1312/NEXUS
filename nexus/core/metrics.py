"""Immutable metric models and pure numeric helpers.

Nothing in this module touches hardware or Qt, which keeps the data layer easy
to unit-test with deterministic fixtures.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, fields
from typing import Iterable, Mapping

# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Capability:
    """Availability of one metric, with a user-facing explanation if absent."""

    key: str
    label: str
    available: bool
    detail: str = ""

    @property
    def status_text(self) -> str:
        return "Available" if self.available else "Unavailable"


# ---------------------------------------------------------------------------
# Component metrics
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CpuMetrics:
    model: str
    utilization_percent: float | None = None
    per_core_percent: tuple[float, ...] = ()
    physical_cores: int | None = None
    logical_cores: int | None = None
    frequency_mhz: float | None = None
    temperature_c: float | None = None


@dataclass(frozen=True, slots=True)
class GpuMetrics:
    name: str
    index: int = 0
    utilization_percent: float | None = None
    memory_used_bytes: int | None = None
    memory_total_bytes: int | None = None
    memory_utilization_percent: float | None = None
    temperature_c: float | None = None
    power_watts: float | None = None
    power_limit_watts: float | None = None
    fan_percent: float | None = None
    core_clock_mhz: float | None = None
    driver_version: str | None = None

    @property
    def memory_percent(self) -> float | None:
        if self.memory_utilization_percent is not None:
            return self.memory_utilization_percent
        if self.memory_used_bytes is None or not self.memory_total_bytes:
            return None
        return min(100.0, 100.0 * self.memory_used_bytes / self.memory_total_bytes)


@dataclass(frozen=True, slots=True)
class MemoryMetrics:
    total_bytes: int
    used_bytes: int
    available_bytes: int
    percent: float
    swap_total_bytes: int | None = None
    swap_used_bytes: int | None = None


@dataclass(frozen=True, slots=True)
class PartitionMetrics:
    device: str
    mountpoint: str
    filesystem: str
    total_bytes: int
    used_bytes: int
    free_bytes: int

    @property
    def percent_used(self) -> float:
        if self.total_bytes <= 0:
            return 0.0
        return 100.0 * self.used_bytes / self.total_bytes


@dataclass(frozen=True, slots=True)
class DiskMetrics:
    partitions: tuple[PartitionMetrics, ...] = ()
    read_bytes_per_sec: float | None = None
    write_bytes_per_sec: float | None = None
    activity_percent: float | None = None

    @property
    def total_bytes(self) -> int:
        return sum(p.total_bytes for p in self.partitions)

    @property
    def used_bytes(self) -> int:
        return sum(p.used_bytes for p in self.partitions)

    @property
    def free_bytes(self) -> int:
        return sum(p.free_bytes for p in self.partitions)


@dataclass(frozen=True, slots=True)
class NetworkAdapter:
    name: str
    received_bytes_per_sec: float | None = None
    sent_bytes_per_sec: float | None = None
    total_received_bytes: int | None = None
    total_sent_bytes: int | None = None
    link_speed_mbps: float | None = None
    is_up: bool = True


@dataclass(frozen=True, slots=True)
class NetworkMetrics:
    interface: str | None = None
    download_bytes_per_sec: float | None = None
    upload_bytes_per_sec: float | None = None
    total_received_bytes: int | None = None
    total_sent_bytes: int | None = None
    adapters: tuple[NetworkAdapter, ...] = ()
    link_speed_mbps: float | None = None


@dataclass(frozen=True, slots=True)
class SystemInfo:
    hostname: str = ""
    os_name: str = ""
    os_version: str = ""
    os_build: str = ""
    architecture: str = ""
    boot_time: float | None = None
    uptime_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class Snapshot:
    """One consistent observation of the machine at ``timestamp``."""

    timestamp: float
    cpu: CpuMetrics | None = None
    gpus: tuple[GpuMetrics, ...] = ()
    memory: MemoryMetrics | None = None
    disk: DiskMetrics | None = None
    network: NetworkMetrics | None = None
    system: SystemInfo | None = None
    warnings: tuple[str, ...] = ()
    collection_ms: float | None = None

    def has_any_data(self) -> bool:
        return bool(self.cpu or self.memory or self.gpus or self.disk or self.network)

    def missing_metrics(self) -> list[str]:
        """Human-readable list of metrics that were unavailable in this sample."""
        missing: list[str] = []
        if self.cpu is None or self.cpu.utilization_percent is None:
            missing.append("CPU utilization")
        if self.cpu is not None and self.cpu.temperature_c is None:
            missing.append("CPU temperature")
        if self.gpus:
            gpu = self.gpus[0]
            if gpu.utilization_percent is None:
                missing.append("GPU utilization")
            if gpu.temperature_c is None:
                missing.append("GPU temperature")
            if gpu.memory_total_bytes is None:
                missing.append("GPU memory")
            if gpu.fan_percent is None:
                missing.append("GPU fan speed")
            if gpu.power_watts is None:
                missing.append("GPU power draw")
        else:
            missing.append("GPU metrics (no supported GPU detected)")
        if self.disk is not None and self.disk.activity_percent is None:
            missing.append("Disk activity")
        return missing


# ---------------------------------------------------------------------------
# Rate / statistics helpers
# ---------------------------------------------------------------------------


class RateTracker:
    """Convert monotonically increasing counters into per-second rates.

    Handles counter resets, duplicate timestamps and non-finite values without
    raising. ``update`` returns ``None`` until two samples are available.
    """

    __slots__ = ("_last_value", "_last_time")

    def __init__(self) -> None:
        self._last_value: float | None = None
        self._last_time: float | None = None

    def reset(self) -> None:
        self._last_value = None
        self._last_time = None

    def update(self, value: float, now: float) -> float | None:
        if not math.isfinite(value) or not math.isfinite(now):
            return None
        previous_value, previous_time = self._last_value, self._last_time
        self._last_value, self._last_time = value, now
        if previous_value is None or previous_time is None:
            return None
        elapsed = now - previous_time
        if elapsed <= 0:
            return None
        delta = value - previous_value
        if delta < 0:
            # Counter reset (adapter reconnect, driver reload). Re-baseline.
            return None
        return delta / elapsed


class RunningStats:
    """Count/min/max/sum accumulator with a defensive copy of values."""
    __slots__ = ("count", "minimum", "maximum", "_total")

    def __init__(self) -> None:
        self.count = 0
        self.minimum: float | None = None
        self.maximum: float | None = None
        self._total = 0.0

    def add(self, value: float | None) -> None:
        if value is None or not math.isfinite(value):
            return
        self.count += 1
        self._total += value
        self.minimum = value if self.minimum is None else min(self.minimum, value)
        self.maximum = value if self.maximum is None else max(self.maximum, value)

    @property
    def average(self) -> float | None:
        return self._total / self.count if self.count else None

    @property
    def is_empty(self) -> bool:
        return self.count == 0


def mean(values: Iterable[float | None]) -> float | None:
    """Mean of finite values, ignoring ``None``. Returns ``None`` if empty."""
    clean = [v for v in values if v is not None and math.isfinite(v)]
    return sum(clean) / len(clean) if clean else None


class SustainedTracker:
    """Time-windowed mean used for "sustained" pressure rules.

    Samples are pruned to ``window_seconds``; an average is only reported once
    ``min_samples`` observations exist, which prevents a single spike from
    triggering a recommendation.
    """

    __slots__ = ("_window", "_min_samples", "_samples")

    def __init__(self, *, window_seconds: float = 20.0, min_samples: int = 5) -> None:
        self._window = max(1.0, float(window_seconds))
        self._min_samples = max(1, int(min_samples))
        self._samples: list[tuple[float, float | None]] = []

    def reset(self) -> None:
        self._samples.clear()

    def add(self, timestamp: float, value: float | None) -> None:
        self._samples.append((timestamp, value))
        cutoff = timestamp - self._window
        self._samples = [sample for sample in self._samples if sample[0] >= cutoff]

    def average(self) -> float | None:
        values = [value for _, value in self._samples if value is not None]
        if len(values) < self._min_samples:
            return None
        return sum(values) / len(values)

    def elapsed(self) -> float:
        if len(self._samples) < 2:
            return 0.0
        return max(0.0, self._samples[-1][0] - self._samples[0][0])

    @property
    def sample_count(self) -> int:
        return len(self._samples)


def peak(values: Iterable[float | None]) -> float | None:
    clean = [v for v in values if v is not None and math.isfinite(v)]
    return max(clean) if clean else None


def coverage(available: int, total: int) -> float:
    """Fraction of expected sensors that produced data (0.0 - 1.0)."""
    if total <= 0:
        return 0.0
    return max(0.0, min(1.0, available / total))


# ---------------------------------------------------------------------------
# Sensor table projection
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SensorReading:
    key: str
    category: str
    label: str
    value: float | None
    unit: str
    note: str = ""


def snapshot_readings(snapshot: Snapshot | None) -> list[SensorReading]:
    """Flatten a snapshot into rows for the Hardware Monitor sensor table."""
    if snapshot is None:
        return []
    rows: list[SensorReading] = []
    cpu = snapshot.cpu
    if cpu is not None:
        rows.append(SensorReading("cpu.util", "CPU", "Total utilization", cpu.utilization_percent, "%"))
        rows.append(
            SensorReading("cpu.freq", "CPU", "Current frequency", cpu.frequency_mhz, "MHz")
        )
        rows.append(
            SensorReading(
                "cpu.temp",
                "CPU",
                "Package temperature",
                cpu.temperature_c,
                "°C",
                "" if cpu.temperature_c is not None else "Not exposed by this system",
            )
        )
    memory = snapshot.memory
    if memory is not None:
        rows.append(SensorReading("mem.percent", "Memory", "Utilization", memory.percent, "%"))
        rows.append(SensorReading("mem.used", "Memory", "Used memory", float(memory.used_bytes), "B"))
        rows.append(
            SensorReading("mem.available", "Memory", "Available memory", float(memory.available_bytes), "B")
        )
    disk = snapshot.disk
    if disk is not None:
        rows.append(
            SensorReading("disk.read", "Storage", "Read throughput", disk.read_bytes_per_sec, "B/s")
        )
        rows.append(
            SensorReading("disk.write", "Storage", "Write throughput", disk.write_bytes_per_sec, "B/s")
        )
        rows.append(
            SensorReading(
                "disk.activity",
                "Storage",
                "Busy time",
                disk.activity_percent,
                "%",
                "" if disk.activity_percent is not None else "Requires disk performance counters",
            )
        )
    network = snapshot.network
    if network is not None:
        rows.append(
            SensorReading("net.down", "Network", "Download", network.download_bytes_per_sec, "B/s")
        )
        rows.append(
            SensorReading("net.up", "Network", "Upload", network.upload_bytes_per_sec, "B/s")
        )
    for index, gpu in enumerate(snapshot.gpus):
        prefix = f"gpu{index}"
        label = f"GPU {index}: {gpu.name}"
        rows.extend(
            [
                SensorReading(f"{prefix}.util", "GPU", f"{label} utilization", gpu.utilization_percent, "%"),
                SensorReading(
                    f"{prefix}.mem",
                    "GPU",
                    f"{label} memory used",
                    float(gpu.memory_used_bytes) if gpu.memory_used_bytes is not None else None,
                    "B",
                ),
                SensorReading(f"{prefix}.temp", "GPU", f"{label} temperature", gpu.temperature_c, "°C"),
                SensorReading(f"{prefix}.power", "GPU", f"{label} power", gpu.power_watts, "W"),
                SensorReading(f"{prefix}.fan", "GPU", f"{label} fan speed", gpu.fan_percent, "%"),
            ]
        )
    return rows


def snapshot_fields() -> list[str]:
    return [f.name for f in fields(Snapshot)]


def snapshot_to_record(snapshot: Snapshot) -> Mapping[str, float | int | None]:
    """Flatten the subset of metrics persisted in the history database."""
    cpu = snapshot.cpu
    memory = snapshot.memory
    disk = snapshot.disk
    network = snapshot.network
    gpu = snapshot.gpus[0] if snapshot.gpus else None
    return {
        "ts": snapshot.timestamp,
        "cpu_percent": cpu.utilization_percent if cpu else None,
        "cpu_temp_c": cpu.temperature_c if cpu else None,
        "memory_percent": memory.percent if memory else None,
        "memory_used_bytes": memory.used_bytes if memory else None,
        "disk_read_bps": disk.read_bytes_per_sec if disk else None,
        "disk_write_bps": disk.write_bytes_per_sec if disk else None,
        "disk_activity_percent": disk.activity_percent if disk else None,
        "net_down_bps": network.download_bytes_per_sec if network else None,
        "net_up_bps": network.upload_bytes_per_sec if network else None,
        "gpu_percent": gpu.utilization_percent if gpu else None,
        "gpu_mem_percent": gpu.memory_percent if gpu else None,
        "gpu_temp_c": gpu.temperature_c if gpu else None,
    }
