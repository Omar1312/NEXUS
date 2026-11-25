from __future__ import annotations

import threading
import time

from nexus.services.process_service import ProcessService


def test_process_service_starts_refreshes_stops_and_restarts(qtbot, monkeypatch):
    calls = []

    class FakeSampler:
        def sample(self):
            calls.append(len(calls) + 1)
            return []

    monkeypatch.setattr("nexus.services.process_service.ProcessSampler", FakeSampler)
    service = ProcessService(interval_ms=60_000)
    results = []
    service.sampleReady.connect(results.append)

    service.set_active(True)
    qtbot.waitUntil(lambda: bool(results), timeout=2000)
    service.refresh_now()
    qtbot.waitUntil(lambda: len(results) >= 2, timeout=2000)
    assert service.shutdown()
    assert not service.active

    service.set_active(True)
    qtbot.waitUntil(lambda: len(results) >= 3, timeout=2000)
    assert service.shutdown()
    assert len(calls) >= 3


def test_process_service_shutdown_is_bounded_and_retains_state_until_exit(qtbot, monkeypatch):
    entered = threading.Event()
    release = threading.Event()

    class SlowSampler:
        def sample(self):
            entered.set()
            release.wait(timeout=2.0)
            return []

    monkeypatch.setattr("nexus.services.process_service.ProcessSampler", SlowSampler)
    monkeypatch.setattr("nexus.services.process_service._PROCESS_STOP_TIMEOUT_MS", 50)
    service = ProcessService()
    service.set_active(True)
    qtbot.waitUntil(entered.is_set, timeout=2000)
    started = time.monotonic()
    assert not service.shutdown()
    assert time.monotonic() - started < 0.5
    assert service.active

    release.set()
    qtbot.waitUntil(lambda: not service.active, timeout=2000)
