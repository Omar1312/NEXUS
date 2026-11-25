"""Aggregate collector that assembles one :class:`Snapshot` per refresh.

Sub-collector failures are isolated: a missing GPU or an access-denied disk is
recorded as a warning while every other metric is still reported.
"""

from __future__ import annotations

import logging
import sys
import time

from nexus.core.metrics import (
    Capability,
    Snapshot,
    SystemInfo,
)
log = logging.getLogger(__name__)


class SystemCollector:
    """Owns all hardware collectors and produces snapshots.

    Construct this object on the thread that will sample it. It is not intended
    to be shared between threads.
    """

    def __init__(self, *, enable_wmi_sensors: bool = True) -> None:
        self._macos = None
        if sys.platform == "darwin":
            from nexus.platforms.macos.collector import MacSystemCollector

            self._macos = MacSystemCollector()
            return
        if sys.platform != "win32":
            from nexus.platforms.selection import platform_id

            platform_id()

        # Keep Windows-only modules out of the macOS import graph.
        from nexus.hardware.cpu import CpuCollector
        from nexus.hardware.disk import DiskCollector
        from nexus.hardware.gpu import GpuCollector
        from nexus.hardware.memory import MemoryCollector
        from nexus.hardware.network import NetworkCollector
        from nexus.hardware.sensors import CpuTemperatureSensor
        from nexus.hardware.windows import os_info

        self._temperature = CpuTemperatureSensor(enabled=enable_wmi_sensors)
        self._cpu = CpuCollector(self._temperature)
        self._memory = MemoryCollector()
        self._disk = DiskCollector()
        self._network = NetworkCollector()
        self._gpu = GpuCollector()
        self._system = os_info()
        self._warnings: list[str] = []
        if not self._gpu.available:
            self._warnings.append(
                "NVIDIA GPU metrics unavailable: NVML could not be initialised."
            )
        if not self._temperature.available:
            self._warnings.append("CPU temperature is not exposed on this system.")

    # -- public API ---------------------------------------------------------
    @property
    def gpu(self) -> GpuCollector:
        if self._macos is not None:
            return None
        return self._gpu

    @property
    def cpu(self) -> CpuCollector:
        if self._macos is not None:
            return self._macos.cpu
        return self._cpu

    def capabilities(self) -> list[Capability]:
        if self._macos is not None:
            return self._macos.capabilities()
        items: list[Capability] = []
        for part in (self._cpu.capabilities(), self._gpu.capabilities()):
            items.extend(part)
        items.extend(
            [
                Capability("mem.usage", "Memory utilization", True, "Windows memory manager"),
                Capability(
                    "disk.activity",
                    "Disk activity",
                    self._has_disk_activity(),
                    "Derived from the Windows disk busy-time counter.",
                ),
                Capability("net.throughput", "Network throughput", True, "Per-adapter byte counters"),
            ]
        )
        return items

    def _has_disk_activity(self) -> bool:
        try:
            import psutil

            counters = psutil.disk_io_counters()
            return counters is not None and getattr(counters, "busy_time", None) is not None
        except Exception:
            return False

    def system_info(self) -> SystemInfo:
        if self._macos is not None:
            return self._macos.system_info()
        base = self._system
        try:
            import psutil

            boot_time = float(psutil.boot_time())
            uptime = max(0.0, time.time() - boot_time)
        except Exception:
            boot_time = uptime = None
        return SystemInfo(
            hostname=base.hostname,
            os_name=base.os_name,
            os_version=base.os_version,
            os_build=base.os_build,
            architecture=base.architecture,
            boot_time=boot_time,
            uptime_seconds=uptime,
        )

    @property
    def _boot_time(self) -> float | None:
        try:
            import psutil

            return float(psutil.boot_time())
        except Exception:
            return None

    def collect(self) -> Snapshot:
        if self._macos is not None:
            return self._macos.collect()
        started = time.perf_counter()
        # Capability warnings from initialisation stay attached to every snapshot;
        # they explain permanently unavailable sensors (CPU temperature, NVML).
        warnings: list[str] = list(self._warnings)

        cpu = memory = disk = network = None
        gpus = ()
        try:
            cpu = self._cpu.sample()
        except Exception as exc:
            log.exception("CPU collection failed")
            warnings.append(f"CPU metrics failed: {exc}")
        try:
            memory = self._memory.sample()
        except Exception as exc:
            log.exception("Memory collection failed")
            warnings.append(f"Memory metrics failed: {exc}")
        try:
            disk = self._disk.sample()
        except Exception as exc:
            log.exception("Disk collection failed")
            warnings.append(f"Disk metrics failed: {exc}")
        try:
            network = self._network.sample()
        except Exception as exc:
            log.exception("Network collection failed")
            warnings.append(f"Network metrics failed: {exc}")
        try:
            gpus = self._gpu.sample()
        except Exception as exc:
            log.exception("GPU collection failed")
            warnings.append(f"GPU metrics failed: {exc}")

        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return Snapshot(
            timestamp=time.time(),
            cpu=cpu,
            gpus=gpus,
            memory=memory,
            disk=disk,
            network=network,
            system=self.system_info(),
            warnings=tuple(warnings),
            collection_ms=round(elapsed_ms, 2),
        )

    def close(self) -> None:
        if self._macos is not None:
            self._macos.close()
            return
        self._cpu.close()
        self._gpu.close()
