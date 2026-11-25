"""Disk capacity and throughput/activity metrics.

Activity (busy time) is derived from the delta of Windows' disk busy counter,
which is a real measurement; when the platform omits it we return ``None``
instead of guessing.
"""

from __future__ import annotations

import logging
import time

import psutil

from nexus.core.metrics import DiskMetrics, PartitionMetrics, RateTracker

log = logging.getLogger(__name__)


class DiskCollector:
    def __init__(self) -> None:
        self._read_rate = RateTracker()
        self._write_rate = RateTracker()
        self._busy_rate = RateTracker()
        self._last_sample_time: float | None = None

    def _partitions(self) -> tuple[PartitionMetrics, ...]:
        partitions: list[PartitionMetrics] = []
        seen: set[str] = set()
        try:
            entries = psutil.disk_partitions(all=False)
        except Exception as exc:
            log.warning("Partition enumeration failed: %s", exc)
            return ()
        for entry in entries:
            if "cdrom" in entry.opts or entry.mountpoint in seen:
                continue
            try:
                usage = psutil.disk_usage(entry.mountpoint)
            except (PermissionError, OSError) as exc:
                log.debug("Skipping inaccessible volume %s: %s", entry.mountpoint, exc)
                continue
            seen.add(entry.mountpoint)
            partitions.append(
                PartitionMetrics(
                    device=entry.device,
                    mountpoint=entry.mountpoint,
                    filesystem=entry.fstype or "Unknown",
                    total_bytes=int(usage.total),
                    used_bytes=int(usage.used),
                    free_bytes=int(usage.free),
                )
            )
        partitions.sort(key=lambda p: p.mountpoint)
        return tuple(partitions)

    def sample(self) -> DiskMetrics:
        now = time.monotonic()
        elapsed = now - self._last_sample_time if self._last_sample_time is not None else None
        self._last_sample_time = now

        read_rate = write_rate = activity = None
        try:
            counters = psutil.disk_io_counters()
        except Exception:
            counters = None
        if counters is not None:
            read_rate = self._read_rate.update(float(counters.read_bytes), now)
            write_rate = self._write_rate.update(float(counters.write_bytes), now)
            busy_time = getattr(counters, "busy_time", None)
            if busy_time is not None:
                busy_delta = self._busy_rate.update(float(busy_time), now)
                if busy_delta is not None and elapsed and elapsed > 0:
                    # RateTracker already divides the millisecond counter delta
                    # by elapsed seconds, yielding busy milliseconds per second.
                    activity = max(0.0, min(100.0, busy_delta / 10.0))
        return DiskMetrics(
            partitions=self._partitions(),
            read_bytes_per_sec=read_rate,
            write_bytes_per_sec=write_rate,
            activity_percent=round(activity, 1) if activity is not None else None,
        )
