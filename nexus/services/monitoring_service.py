"""Own the hardware sampling thread and publish immutable metric snapshots."""

from __future__ import annotations

import logging
import threading
import time
import traceback
from typing import Callable

from PySide6.QtCore import QCoreApplication, QEventLoop, QObject, QThread, Signal, Slot

from nexus.core.collectors import SystemCollector
from nexus.core.metrics import Capability, Snapshot

log = logging.getLogger(__name__)
_STOP_TIMEOUT_MS = 5000


class _MetricsThread(QThread):
    """Run collectors directly in QThread.run, avoiding cross-thread QObject ownership."""

    snapshotReady = Signal(object)
    capabilitiesReady = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        interval_ms: int,
        enable_wmi_sensors: bool,
        collector_factory: Callable[..., SystemCollector],
        parent: QObject,
    ) -> None:
        super().__init__(parent)
        self._interval_ms = max(250, interval_ms)
        self._interval_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        self._enable_wmi = enable_wmi_sensors
        self._collector_factory = collector_factory

    def request_stop(self) -> None:
        self._stop_event.set()
        self._wake_event.set()

    def request_sample(self) -> None:
        self._wake_event.set()

    def set_interval(self, milliseconds: int) -> None:
        with self._interval_lock:
            self._interval_ms = max(250, int(milliseconds))
        self._wake_event.set()

    def run(self) -> None:
        collector = None
        try:
            collector = self._collector_factory(enable_wmi_sensors=self._enable_wmi)
            self.capabilitiesReady.emit(collector.capabilities())
            self._sample(collector)
            while not self._stop_event.is_set():
                with self._interval_lock:
                    timeout = self._interval_ms / 1000.0
                self._wake_event.wait(timeout)
                self._wake_event.clear()
                if not self._stop_event.is_set():
                    self._sample(collector)
        except Exception:
            self.failed.emit(
                "Hardware collectors could not be initialized or sampled:\n"
                + traceback.format_exc(limit=3)
            )
        finally:
            if collector is not None:
                try:
                    collector.close()
                except Exception:
                    log.debug("Collector shutdown error", exc_info=True)
            log.info("Metrics thread stopped.")

    def _sample(self, collector: SystemCollector) -> None:
        try:
            self.snapshotReady.emit(collector.collect())
        except Exception:
            log.exception("Snapshot collection crashed")
            self.failed.emit("System metrics could not be collected. See the log for details.")


class MonitoringService(QObject):
    """Owns the sampling thread and exposes the latest snapshot."""

    snapshotReady = Signal(object)
    capabilitiesReady = Signal(object)
    errorOccurred = Signal(str)
    runningChanged = Signal(bool)
    intervalChanged = Signal(int)

    def __init__(
        self,
        *,
        interval_s: int = 2,
        enable_wmi_sensors: bool = True,
        collector_factory: Callable[..., SystemCollector] = SystemCollector,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._interval_s = max(1, int(interval_s))
        self._enable_wmi = enable_wmi_sensors
        self._collector_factory = collector_factory
        self._thread: _MetricsThread | None = None
        self._restart_pending = False
        self._latest: Snapshot | None = None
        self._capabilities: list[Capability] = []
        self._last_update: float | None = None
        self._errors = 0

    @property
    def latest(self) -> Snapshot | None:
        return self._latest

    @property
    def capabilities(self) -> list[Capability]:
        return list(self._capabilities)

    @property
    def last_update(self) -> float | None:
        return self._last_update

    @property
    def interval_s(self) -> int:
        return self._interval_s

    @property
    def running(self) -> bool:
        # Remain logically active until the owner-thread finished callback has
        # released the QThread wrapper, not merely until the OS thread exits.
        return self._thread is not None

    @property
    def consecutive_errors(self) -> int:
        return self._errors

    def start(self) -> None:
        if self._thread is not None:
            if self._thread.isRunning():
                self._thread.request_sample()
            else:
                self._restart_pending = True
            return
        thread = _MetricsThread(
            self._interval_s * 1000,
            self._enable_wmi,
            self._collector_factory,
            self,
        )
        thread.snapshotReady.connect(self._on_snapshot)
        thread.capabilitiesReady.connect(self._on_capabilities)
        thread.failed.connect(self._on_error)
        thread.finished.connect(self._on_thread_finished)
        self._thread = thread
        thread.start()
        self.runningChanged.emit(True)
        log.info("Monitoring started at %ss interval.", self._interval_s)

    def stop(self) -> bool:
        thread = self._thread
        if thread is None:
            return True
        if thread.isRunning():
            thread.request_stop()
            if not thread.wait(_STOP_TIMEOUT_MS):
                message = f"Monitoring worker did not stop within {_STOP_TIMEOUT_MS / 1000:g} seconds."
                log.warning(message)
                self.errorOccurred.emit(message)
                return False
        app = QCoreApplication.instance()
        if app is not None:
            for _ in range(3):
                QCoreApplication.processEvents(QEventLoop.ProcessEventsFlag.AllEvents)
                if self._thread is None:
                    break
        return self._thread is None

    def refresh_now(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            self._thread.request_sample()

    def set_interval(self, seconds: int) -> None:
        seconds = max(1, min(60, int(seconds)))
        if seconds == self._interval_s:
            return
        self._interval_s = seconds
        if self._thread is not None and self._thread.isRunning():
            self._thread.set_interval(seconds * 1000)
        self.intervalChanged.emit(seconds)
        log.info("Monitoring interval set to %ss.", seconds)

    def set_log_level(self, level: str) -> None:
        from nexus.utils.logging_config import set_log_level

        set_log_level(level)

    @Slot(object)
    def _on_snapshot(self, snapshot: Snapshot) -> None:
        self._latest = snapshot
        self._last_update = time.time()
        self._errors = 0
        self.snapshotReady.emit(snapshot)
        if snapshot.warnings:
            log.debug("Snapshot warnings: %s", "; ".join(snapshot.warnings))

    @Slot(object)
    def _on_capabilities(self, capabilities: list[Capability]) -> None:
        self._capabilities = list(capabilities)
        self.capabilitiesReady.emit(capabilities)

    @Slot(str)
    def _on_error(self, message: str) -> None:
        self._errors += 1
        log.warning("Monitoring error #%d: %s", self._errors, message)
        self.errorOccurred.emit(message)

    @Slot()
    def _on_thread_finished(self) -> None:
        finished_thread = self.sender()
        if finished_thread is not self._thread:
            return
        self._thread = None
        finished_thread.deleteLater()
        self.runningChanged.emit(False)
        if self._restart_pending:
            self._restart_pending = False
            self.start()
