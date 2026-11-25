"""Least-privilege macOS baseline collectors built on psutil."""

from __future__ import annotations

import logging
import platform
import subprocess
import time
from typing import Any

import psutil

from nexus.core.metrics import (
    Capability,
    CpuMetrics,
    MemoryMetrics,
    Snapshot,
    SystemInfo,
)
from nexus.hardware.disk import DiskCollector
from nexus.hardware.network import NetworkCollector

log = logging.getLogger(__name__)


class MacSystemCollector:
    """Collect cross-platform base metrics without privileged/private APIs.

    Apple Silicon GPU memory is part of the system memory pool. This backend
    reports system RAM once and does not invent a dedicated VRAM value.
    """

    def __init__(
        self,
        *,
        psutil_module: Any = psutil,
        platform_module: Any = platform,
        disk_collector: Any | None = None,
        network_collector: Any | None = None,
    ) -> None:
        self._psutil = psutil_module
        self._platform = platform_module
        self._disk = disk_collector or DiskCollector()
        self._network = network_collector or NetworkCollector()
        self._architecture = str(self._platform.machine() or "unknown")
        self._cpu_model = self._model_name()
        self._physical_cores = self._safe_cpu_count(logical=False)
        self._logical_cores = self._safe_cpu_count(logical=True)
        try:
            self._psutil.cpu_percent(interval=None)
            self._psutil.cpu_percent(interval=None, percpu=True)
        except (OSError, RuntimeError) as exc:
            log.debug("Could not prime macOS CPU counters: %s", exc)

    def _model_name(self) -> str:
        for value in (
            self._platform.processor(),
            getattr(self._platform.uname(), "processor", ""),
        ):
            if value and str(value).strip() and str(value).lower() not in {"arm", "i386"}:
                return " ".join(str(value).split())
        try:
            result = subprocess.run(
                ["/usr/sbin/sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True, timeout=1.0, check=True,
            )
            value = result.stdout.strip()
            if value:
                return " ".join(value.split())[:160]
        except (OSError, subprocess.SubprocessError):
            pass
        if self._architecture.casefold() in {"arm64", "aarch64"}:
            return "Apple Silicon CPU (model unavailable)"
        if self._architecture.casefold() in {"x86_64", "amd64"}:
            return "Intel CPU (model unavailable)"
        return "CPU model unavailable"

    def _safe_cpu_count(self, *, logical: bool) -> int | None:
        try:
            value = self._psutil.cpu_count(logical=logical)
            return int(value) if value else None
        except (OSError, RuntimeError, TypeError, ValueError):
            return None

    @property
    def cpu(self):
        return self

    def capabilities(self) -> list[Capability]:
        try:
            counters = self._psutil.disk_io_counters()
            disk_activity = counters is not None and getattr(counters, "busy_time", None) is not None
        except (OSError, RuntimeError):
            disk_activity = False
        return [
            Capability("cpu.usage", "CPU utilization", True, "psutil CPU time counters"),
            Capability("cpu.frequency", "CPU frequency", False, "Not exposed by psutil on macOS."),
            Capability("cpu.temperature", "CPU temperature", False, "No supported sensor backend configured."),
            Capability("gpu.utilization", "GPU utilization", False, "Not available in the least-privilege baseline."),
            Capability("gpu.memory", "GPU memory", False, "Apple Silicon uses unified system memory."),
            Capability("mem.usage", "System memory utilization", True, "psutil virtual memory; includes unified RAM."),
            Capability("mem.pressure", "Memory pressure", False, "A supported pressure source is not configured."),
            Capability("disk.activity", "Disk activity", disk_activity, "Reported only if the OS exposes a busy-time counter."),
            Capability("disk.throughput", "Disk throughput", True, "psutil disk I/O byte counters."),
            Capability("net.throughput", "Network throughput", True, "psutil per-interface byte counters."),
        ]

    def system_info(self) -> SystemInfo:
        try:
            os_version = str(self._platform.mac_ver()[0] or self._platform.release())
        except (AttributeError, OSError):
            os_version = str(self._platform.release())
        try:
            boot_time = float(self._psutil.boot_time())
            uptime = max(0.0, time.time() - boot_time)
        except (OSError, RuntimeError, TypeError, ValueError):
            boot_time = uptime = None
        return SystemInfo(
            hostname=str(self._platform.node() or ""),
            os_name="macOS",
            os_version=os_version,
            os_build="",
            architecture=self._architecture,
            boot_time=boot_time,
            uptime_seconds=uptime,
        )

    def _cpu_sample(self) -> CpuMetrics:
        total = self._psutil.cpu_percent(interval=None)
        per_core = self._psutil.cpu_percent(interval=None, percpu=True)
        return CpuMetrics(
            model=self._cpu_model,
            utilization_percent=_valid_percent(total),
            per_core_percent=tuple(
                value for raw in per_core if (value := _valid_percent(raw)) is not None
            ),
            physical_cores=self._physical_cores,
            logical_cores=self._logical_cores,
            frequency_mhz=None,
            temperature_c=None,
        )

    def _memory_sample(self) -> MemoryMetrics:
        memory = self._psutil.virtual_memory()
        swap = self._psutil.swap_memory()
        total = max(0, int(memory.total))
        available = max(0, min(total, int(memory.available)))
        return MemoryMetrics(
            total_bytes=total,
            used_bytes=max(0, total - available),
            available_bytes=available,
            percent=round(100 * (total - available) / total, 1) if total else 0.0,
            swap_total_bytes=max(0, int(swap.total)),
            swap_used_bytes=max(0, int(swap.used)),
        )

    def collect(self) -> Snapshot:
        started = time.perf_counter()
        warnings = [
            "GPU utilization, temperature, and power are unavailable in this macOS build.",
            "Memory pressure, CPU frequency, and thermal sensors are unavailable.",
        ]
        cpu = memory = disk = network = None
        for name, getter in (
            ("CPU", self._cpu_sample),
            ("memory", self._memory_sample),
            ("disk", self._disk.sample),
            ("network", self._network.sample),
        ):
            try:
                value = getter()
            except Exception as exc:
                log.exception("macOS %s collection failed", name)
                warnings.append(f"{name.capitalize()} metrics unavailable: {exc}")
                continue
            if name == "CPU":
                cpu = value
            elif name == "memory":
                memory = value
            elif name == "disk":
                disk = value
            else:
                network = value
        elapsed = (time.perf_counter() - started) * 1000
        return Snapshot(
            timestamp=time.time(),
            cpu=cpu,
            gpus=(),
            memory=memory,
            disk=disk,
            network=network,
            system=self.system_info(),
            warnings=tuple(warnings),
            collection_ms=round(elapsed, 2),
        )

    def close(self) -> None:
        close = getattr(self._disk, "close", None)
        if close is not None:
            close()


def _valid_percent(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not 0.0 <= number <= 100.0:
        return None
    return round(number, 1)
