from __future__ import annotations

from types import SimpleNamespace

from nexus.core.metrics import DiskMetrics, NetworkMetrics
from nexus.platforms.macos.collector import MacSystemCollector


class FakePsutil:
    def __init__(self) -> None:
        self.cpu_samples = iter((0.0, [0.0, 0.0], 12.5, [0.0, 10.5, 22.0, 100.0]))

    def cpu_percent(self, interval=None, percpu=False):
        return next(self.cpu_samples)

    def cpu_count(self, logical=True):
        return 8 if logical else 4

    def disk_io_counters(self):
        return SimpleNamespace(busy_time=None)

    def virtual_memory(self):
        return SimpleNamespace(total=16_000, available=4_000)

    def swap_memory(self):
        return SimpleNamespace(total=2_000, used=300)

    def boot_time(self):
        return 900.0


class FakePlatform:
    def machine(self):
        return "arm64"

    def processor(self):
        return ""

    def uname(self):
        return SimpleNamespace(processor="arm")

    def mac_ver(self):
        return ("14.0", ("", "", ""), "arm64")

    def release(self):
        return "23.0.0"

    def node(self):
        return "test-mac"


def test_macos_snapshot_reports_unified_ram_without_fabricated_gpu() -> None:
    collector = MacSystemCollector(
        psutil_module=FakePsutil(),
        platform_module=FakePlatform(),
        disk_collector=SimpleNamespace(sample=lambda: DiskMetrics(activity_percent=None)),
        network_collector=SimpleNamespace(sample=lambda: NetworkMetrics()),
    )

    snapshot = collector.collect()

    assert snapshot.cpu is not None
    assert snapshot.cpu.model == "Apple Silicon CPU (model unavailable)"
    assert snapshot.cpu.utilization_percent == 12.5
    assert snapshot.cpu.per_core_percent == (0.0, 10.5, 22.0, 100.0)
    assert snapshot.cpu.frequency_mhz is None
    assert snapshot.gpus == ()
    assert snapshot.memory is not None
    assert snapshot.memory.total_bytes == 16_000
    assert snapshot.memory.used_bytes == 12_000
    assert snapshot.memory.available_bytes == 4_000
    assert snapshot.memory.swap_used_bytes == 300
    assert snapshot.system is not None
    assert snapshot.system.os_name == "macOS"
    assert snapshot.system.architecture == "arm64"
    assert any("GPU utilization" in item for item in snapshot.warnings)
    assert any(item.key == "gpu.memory" and not item.available for item in collector.capabilities())


def test_macos_intel_model_does_not_claim_apple_silicon() -> None:
    platform_module = FakePlatform()
    platform_module.machine = lambda: "x86_64"
    collector = MacSystemCollector(
        psutil_module=FakePsutil(),
        platform_module=platform_module,
        disk_collector=SimpleNamespace(sample=lambda: DiskMetrics()),
        network_collector=SimpleNamespace(sample=lambda: NetworkMetrics()),
    )
    assert collector.cpu._cpu_model == "Intel CPU (model unavailable)"
