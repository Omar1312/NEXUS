"""Physical memory metrics via psutil."""

from __future__ import annotations

from nexus.core.metrics import MemoryMetrics


class MemoryCollector:
    def sample(self) -> MemoryMetrics:
        import psutil

        memory = psutil.virtual_memory()
        swap_total = swap_used = None
        try:
            swap = psutil.swap_memory()
            swap_total = int(swap.total)
            swap_used = int(swap.used)
        except Exception:
            pass
        return MemoryMetrics(
            total_bytes=int(memory.total),
            used_bytes=int(memory.total - memory.available),
            available_bytes=int(memory.available),
            percent=round(float(memory.percent), 1),
            swap_total_bytes=swap_total,
            swap_used_bytes=swap_used,
        )
