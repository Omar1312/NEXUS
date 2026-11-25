"""Process-list sampling without cross-thread QObject ownership."""

from __future__ import annotations

import logging
import threading
import traceback

from PySide6.QtCore import QCoreApplication, QEventLoop, QObject, QThread, Signal, Slot

from nexus.core.process_manager import ProcessInfo, ProcessSampler

log = logging.getLogger(__name__)
_PROCESS_STOP_TIMEOUT_MS = 4000


class _ProcessSamplingThread(QThread):
    sampleReady = Signal(object)
    failed = Signal(str)

    def __init__(self, interval_ms: int, parent: QObject) -> None:
        super().__init__(parent)
        self._interval_ms = max(1000, interval_ms)
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()

    def request_stop(self) -> None:
        self._stop_event.set()
        self._wake_event.set()

    def request_sample(self) -> None:
        self._wake_event.set()

    def run(self) -> None:
        try:
            sampler = ProcessSampler()
            self._sample(sampler)
            while not self._stop_event.is_set():
                self._wake_event.wait(self._interval_ms / 1000.0)
                self._wake_event.clear()
                if not self._stop_event.is_set():
                    self._sample(sampler)
        except Exception:
            log.exception("Process sampling thread failed")
            self.failed.emit("Process enumeration could not be initialized.")

    def _sample(self, sampler: ProcessSampler) -> None:
        try:
            self.sampleReady.emit(sampler.sample())
        except Exception:
            log.exception("Process sampling failed")
            self.failed.emit("The process list could not be read.")


class ProcessService(QObject):
    sampleReady = Signal(object)
    errorOccurred = Signal(str)
    activeChanged = Signal(bool)

    def __init__(self, *, interval_ms: int = 2000, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._interval_ms = max(1000, int(interval_ms))
        self._thread: _ProcessSamplingThread | None = None
        self._restart_pending = False
        self._latest: list[ProcessInfo] = []
        self._active = False

    @property
    def latest(self) -> list[ProcessInfo]:
        return self._latest

    @property
    def active(self) -> bool:
        return self._active or self._thread is not None

    def set_active(self, active: bool) -> None:
        if active and not self.active:
            self._start()
        elif not active and self.active:
            self._stop()

    def refresh_now(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            self._thread.request_sample()

    def _start(self) -> None:
        if self._thread is not None:
            if self._thread.isRunning():
                return
            self._restart_pending = True
            return
        thread = _ProcessSamplingThread(self._interval_ms, self)
        thread.sampleReady.connect(self._on_sample)
        thread.failed.connect(self._on_error)
        thread.finished.connect(self._on_thread_finished)
        self._thread = thread
        self._active = True
        thread.start()
        self.activeChanged.emit(True)

    def _stop(self) -> bool:
        thread = self._thread
        if thread is None:
            self._active = False
            return True
        if thread.isRunning():
            thread.request_stop()
            if not thread.wait(_PROCESS_STOP_TIMEOUT_MS):
                message = "Process sampling did not stop within 4 seconds."
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

    def _on_sample(self, processes: list[ProcessInfo]) -> None:
        self._latest = processes
        self.sampleReady.emit(processes)

    def _on_error(self, message: str) -> None:
        log.warning("Process service: %s", message)
        self.errorOccurred.emit(message)

    @Slot()
    def _on_thread_finished(self) -> None:
        finished_thread = self.sender()
        if finished_thread is not self._thread:
            return
        self._thread = None
        self._active = False
        finished_thread.deleteLater()
        self.activeChanged.emit(False)
        if self._restart_pending:
            self._restart_pending = False
            self._start()

    def shutdown(self) -> bool:
        return self._stop()
