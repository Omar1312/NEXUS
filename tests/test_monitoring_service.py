"""Lifecycle tests for the asynchronous monitoring service."""

from __future__ import annotations

import threading
import time

from nexus.core.metrics import Snapshot
from nexus.services.monitoring_service import MonitoringService


class FakeCollector:
    def __init__(self, *, enable_wmi_sensors: bool) -> None:
        self.enable_wmi_sensors = enable_wmi_sensors
        self.closed = False

    def capabilities(self):
        return []

    def collect(self):
        return Snapshot(timestamp=1.0)

    def close(self):
        self.closed = True


def test_monitoring_service_starts_stops_and_restarts(qtbot):
    collectors = []

    def factory(*, enable_wmi_sensors):
        collector = FakeCollector(enable_wmi_sensors=enable_wmi_sensors)
        collectors.append(collector)
        return collector

    service = MonitoringService(
        interval_s=60, enable_wmi_sensors=False, collector_factory=factory
    )
    snapshots = []
    service.snapshotReady.connect(snapshots.append)

    service.start()
    qtbot.waitUntil(lambda: bool(snapshots), timeout=2000)
    service.start()  # A repeated start requests one refresh, not a second worker.
    qtbot.wait(50)
    assert len(collectors) == 1
    assert collectors[0].enable_wmi_sensors is False

    service.set_interval(1)
    assert service.interval_s == 1
    service.stop()
    assert not service.running
    assert collectors[0].closed

    service.start()
    qtbot.waitUntil(lambda: len(snapshots) >= 2, timeout=2000)
    service.stop()
    assert len(collectors) == 2
    assert all(collector.closed for collector in collectors)


def test_initialization_failure_reports_error_and_allows_restart(qtbot):
    attempts = 0
    snapshots = []
    errors = []

    def factory(*, enable_wmi_sensors):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("fixture initialization failure")
        return FakeCollector(enable_wmi_sensors=enable_wmi_sensors)

    service = MonitoringService(collector_factory=factory)
    service.snapshotReady.connect(snapshots.append)
    service.errorOccurred.connect(errors.append)

    service.start()
    qtbot.waitUntil(lambda: bool(errors), timeout=2000)
    qtbot.waitUntil(lambda: not service.running, timeout=2000)

    service.start()
    qtbot.waitUntil(lambda: bool(snapshots), timeout=2000)
    assert attempts == 2
    service.stop()
    assert not service.running


def test_slow_collection_shutdown_is_bounded_and_finishes_after_release(qtbot, monkeypatch):
    entered_collect = threading.Event()
    release_collect = threading.Event()
    collectors = []
    errors = []

    class SlowCollector(FakeCollector):
        def collect(self):
            entered_collect.set()
            release_collect.wait(timeout=2.0)
            return Snapshot(timestamp=2.0)

    def factory(*, enable_wmi_sensors):
        collector = SlowCollector(enable_wmi_sensors=enable_wmi_sensors)
        collectors.append(collector)
        return collector

    monkeypatch.setattr("nexus.services.monitoring_service._STOP_TIMEOUT_MS", 50)
    service = MonitoringService(collector_factory=factory)
    service.errorOccurred.connect(errors.append)
    service.start()
    qtbot.waitUntil(entered_collect.is_set, timeout=2000)

    started = time.monotonic()
    service.stop()
    elapsed = time.monotonic() - started

    assert elapsed < 0.5
    assert service.running
    assert errors and "did not stop" in errors[-1]

    release_collect.set()
    qtbot.waitUntil(lambda: not service.running, timeout=2000)
    assert collectors[0].closed
