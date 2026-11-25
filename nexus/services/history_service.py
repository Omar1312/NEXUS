"""Background history persistence with bounded queue and batched writes."""

from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Mapping

from PySide6.QtCore import QObject, Signal

from nexus.core.metrics import Snapshot, snapshot_to_record
from nexus.core.scoring import ScoreInput, compute_score
from nexus.database.repository import HistoryRepository
from nexus.utils.exceptions import DatabaseError

log = logging.getLogger(__name__)

_SENTINEL = object()


class HistoryRecorder(QObject):
    """Receives snapshots on the GUI thread and writes them off-thread."""

    errorOccurred = Signal(str)
    droppedSamples = Signal(int)

    def __init__(
        self,
        repository: HistoryRepository,
        *,
        enabled: bool = True,
        retention_days: int = 14,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._repository = repository
        self._enabled = enabled
        self._retention_days = max(1, int(retention_days))
        self._queue: queue.Queue[object] = queue.Queue(maxsize=500)
        self._thread = threading.Thread(target=self._run, name="nexus-history", daemon=True)
        self._stop_event = threading.Event()
        self._dropped = 0

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        log.info("History recording %s.", "enabled" if enabled else "disabled")

    def set_retention_days(self, days: int) -> None:
        self._retention_days = max(1, int(days))

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self) -> bool:
        self._stop_event.set()
        try:
            self._queue.put_nowait(_SENTINEL)
        except queue.Full:
            pass
        if self._thread.is_alive():
            self._thread.join(timeout=4.0)
        return not self._thread.is_alive()

    def handle_snapshot(self, snapshot: Snapshot) -> None:
        if not self._enabled or not snapshot.has_any_data():
            return
        record = dict(snapshot_to_record(snapshot))
        try:
            record["score"] = compute_score(ScoreInput.from_snapshot(snapshot)).total
        except Exception:  # pragma: no cover - scoring is defensive
            record["score"] = None
        try:
            self._queue.put_nowait(record)
        except queue.Full:
            self._dropped += 1
            if self._dropped % 50 == 1:
                self.droppedSamples.emit(self._dropped)

    def _run(self) -> None:
        self._prune()
        batch: list[Mapping[str, float | int | None]] = []
        last_flush = time.monotonic()
        while True:
            if self._stop_event.is_set() and self._queue.empty():
                break
            try:
                item = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            if isinstance(item, dict):
                batch.append(item)  # type: ignore[arg-type]
            if item is _SENTINEL:
                break
            now = time.monotonic()
            if batch and (len(batch) >= 40 or now - last_flush >= 2.0):
                self._flush(batch)
                batch.clear()
                last_flush = now
        if batch:
            self._flush(batch)

    def _flush(self, batch: list[Mapping[str, float | int | None]]) -> None:
        try:
            self._repository.insert_many(batch)
        except DatabaseError as exc:
            log.error("History write failed: %s", exc)
            self.errorOccurred.emit("Performance history could not be saved. Check the log.")

    def _prune(self) -> None:
        cutoff = time.time() - self._retention_days * 86_400
        try:
            removed = self._repository.prune_older_than(cutoff)
            if removed:
                log.info("Pruned %d expired history rows (retention %dd).", removed, self._retention_days)
        except DatabaseError as exc:
            log.warning("History pruning failed: %s", exc)
