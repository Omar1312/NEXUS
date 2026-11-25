"""Run one function on a short-lived QThread and deliver the result safely."""

from __future__ import annotations

import logging
import threading
import traceback
from typing import Any, Callable

from PySide6.QtCore import QObject, QThread, Signal

log = logging.getLogger(__name__)


class _TaskWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, func: Callable[..., Any], args: tuple, kwargs: dict) -> None:
        super().__init__()
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:
        try:
            result = self._func(*self._args, **self._kwargs)
        except Exception as exc:
            log.exception("Background task failed")
            detail = "".join(traceback.format_exception_only(type(exc), exc)).strip()
            self.failed.emit(detail)
            return
        self.finished.emit(result)


class BackgroundTask(QObject):
    """Owner-scoped background operation with progress and cancellation.

    Keep a reference to the returned task for its lifetime; the owning widget
    does this in ``self._tasks``.
    """

    finished = Signal(object)
    failed = Signal(str)
    progress = Signal(object)

    def __init__(
        self,
        func: Callable[..., Any],
        *args: Any,
        cancel_event: threading.Event | None = None,
        parent: QObject | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent)
        self._cancel_event = cancel_event or threading.Event()
        self._thread = QThread(self)
        self._worker = _TaskWorker(func, args, kwargs)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._done = False

    @property
    def cancel_event(self) -> threading.Event:
        return self._cancel_event

    def cancel(self) -> None:
        self._cancel_event.set()

    @property
    def running(self) -> bool:
        return not self._done

    def start(self) -> None:
        self._thread.start()

    def _finish(self) -> None:
        self._done = True
        self._thread.quit()
        self._thread.wait(5000)

    def _on_finished(self, result: object) -> None:
        self._finish()
        self.finished.emit(result)

    def _on_failed(self, message: str) -> None:
        self._finish()
        self.failed.emit(message)
