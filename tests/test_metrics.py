"""Deterministic tests for platform-independent metric calculations."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from nexus.core.metrics import RateTracker
from nexus.hardware.cpu import CpuCollector
from nexus.hardware.disk import DiskCollector
from nexus.hardware.memory import MemoryCollector
from nexus.hardware.network import NetworkCollector


def test_rate_tracker_requires_baseline_and_computes_rate():
    tracker = RateTracker()

    assert tracker.update(100.0, 10.0) is None
    assert tracker.update(160.0, 12.0) == 30.0


def test_rate_tracker_invalid_or_nonpositive_interval_is_unavailable():
    tracker = RateTracker()
    tracker.update(10.0, 5.0)

    assert tracker.update(20.0, 5.0) is None
    assert tracker.update(float("nan"), 6.0) is None


def test_rate_tracker_counter_reset_rebaselines_without_reporting_zero():
    tracker = RateTracker()
    tracker.update(100.0, 1.0)

    assert tracker.update(10.0, 2.0) is None
    assert tracker.update(50.0, 4.0) == 20.0


def test_cpu_collector_preserves_total_and_per_core_psutil_values():
    class FakePdh:
        def read_percent(self):
            return None

        def close(self):
            pass

    psutil_samples = iter([0.0, [0.0, 0.0], 37.5, [25.0, 50.0]])

    def cpu_percent(*, interval=None, percpu=False):
        return next(psutil_samples)

    temperature = SimpleNamespace(read=lambda: SimpleNamespace(celsius=None))
    with (
        patch("nexus.hardware.cpu.cpu_brand", return_value="Fixture CPU"),
        patch("nexus.hardware.cpu._PdhQuery", FakePdh),
        patch("nexus.hardware.cpu.psutil.cpu_count", side_effect=lambda logical: 8 if logical else 4),
        patch("nexus.hardware.cpu.psutil.cpu_freq", return_value=None, create=True),
        patch("nexus.hardware.cpu.psutil.cpu_percent", side_effect=cpu_percent),
    ):
        collector = CpuCollector(temperature_sensor=temperature)
        sample = collector.sample()

    assert sample.utilization_percent == 37.5
    assert sample.per_core_percent == (25.0, 50.0)
    assert sample.physical_cores == 4
    assert sample.logical_cores == 8


def test_memory_collector_reports_total_minus_available_and_swap():
    memory = SimpleNamespace(total=1000, available=250, percent=75.0)
    swap = SimpleNamespace(total=400, used=125)
    with (
        patch("psutil.virtual_memory", return_value=memory),
        patch("psutil.swap_memory", return_value=swap),
    ):
        sample = MemoryCollector().sample()

    assert sample.total_bytes == 1000
    assert sample.available_bytes == 250
    assert sample.used_bytes == 750
    assert sample.percent == 75.0
    assert sample.swap_total_bytes == 400
    assert sample.swap_used_bytes == 125


def test_disk_throughput_uses_delta_and_first_sample_is_unavailable():
    collector = DiskCollector()
    counters = [
        type("Counters", (), {"read_bytes": 100, "write_bytes": 200, "busy_time": 1000})(),
        type("Counters", (), {"read_bytes": 500, "write_bytes": 600, "busy_time": 1500})(),
    ]
    with (
        patch("nexus.hardware.disk.time.monotonic", side_effect=[10.0, 12.0]),
        patch("nexus.hardware.disk.psutil.disk_io_counters", side_effect=counters),
        patch("nexus.hardware.disk.psutil.disk_partitions", return_value=[]),
    ):
        first = collector.sample()
        second = collector.sample()

    assert first.read_bytes_per_sec is None
    assert second.read_bytes_per_sec == 200.0
    assert second.write_bytes_per_sec == 200.0
    assert second.activity_percent == 25.0


def test_network_rates_are_per_adapter_and_first_sample_is_unavailable():
    collector = NetworkCollector()
    counters = [
        {"Ethernet": type("Counter", (), {"bytes_recv": 100, "bytes_sent": 200})()},
        {"Ethernet": type("Counter", (), {"bytes_recv": 500, "bytes_sent": 600})()},
    ]
    stats = {"Ethernet": type("Stats", (), {"isup": True, "speed": 1000})()}
    with (
        patch("nexus.hardware.network.time.monotonic", side_effect=[10.0, 12.0]),
        patch("nexus.hardware.network.psutil.net_io_counters", side_effect=counters),
        patch("nexus.hardware.network.psutil.net_if_stats", return_value=stats),
    ):
        first = collector.sample()
        second = collector.sample()

    assert first.download_bytes_per_sec is None
    assert second.download_bytes_per_sec == 200.0
    assert second.upload_bytes_per_sec == 200.0
