"""Thread-safe repository for metrics and gaming sessions."""

from __future__ import annotations

import csv
import io
import json
import logging
import sqlite3
import threading
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from nexus.database.connection import Database
from nexus.database.models import GamingSessionRow, MetricRow
from nexus.utils.exceptions import DatabaseError

log = logging.getLogger(__name__)

NUMERIC_COLUMNS = (
    "cpu_percent",
    "cpu_temp_c",
    "memory_percent",
    "memory_used_bytes",
    "disk_read_bps",
    "disk_write_bps",
    "disk_activity_percent",
    "net_down_bps",
    "net_up_bps",
    "gpu_percent",
    "gpu_mem_percent",
    "gpu_temp_c",
    "score",
)

CSV_HEADER = ("timestamp_iso", "timestamp_epoch", *NUMERIC_COLUMNS)


@dataclass(frozen=True, slots=True)
class StorageStats:
    rows: int
    oldest_ts: float | None
    newest_ts: float | None
    file_size_bytes: int


class HistoryRepository:
    """All SQL lives here. Instances are safe to share across threads."""

    def __init__(self, database: Database) -> None:
        self._database = database
        self._lock = threading.RLock()
        self._database.connect()

    # -- writes -------------------------------------------------------------
    def insert_metric(self, record: Mapping[str, float | int | None]) -> None:
        self.insert_many([record])

    def insert_many(self, records: Iterable[Mapping[str, float | int | None]]) -> None:
        rows = [
            tuple(record.get(column) for column in ("ts", *NUMERIC_COLUMNS))
            for record in records
            if record.get("ts") is not None
        ]
        if not rows:
            return
        placeholders = ", ".join("?" for _ in range(len(NUMERIC_COLUMNS) + 1))
        columns = ", ".join(("ts", *NUMERIC_COLUMNS))
        try:
            with self._lock:
                with self._database.connection as connection:
                    connection.executemany(
                        f"INSERT INTO metrics ({columns}) VALUES ({placeholders})", rows
                    )
        except sqlite3.DatabaseError as exc:
            raise DatabaseError(f"Metric insert failed: {exc}") from exc

    # -- reads --------------------------------------------------------------
    def count(self) -> int:
        with self._lock:
            row = self._database.connection.execute("SELECT COUNT(*) FROM metrics").fetchone()
        return int(row[0]) if row else 0

    def query_range(
        self, start_ts: float, end_ts: float, *, limit: int | None = None
    ) -> list[MetricRow]:
        if end_ts <= start_ts:
            return []
        sql = (
            "SELECT ts, " + ", ".join(NUMERIC_COLUMNS) + " FROM metrics "
            "WHERE ts >= ? AND ts <= ? ORDER BY ts ASC"
        )
        params: list[float | int] = [start_ts, end_ts]
        if limit and limit > 0:
            sql += " LIMIT ?"
            params.append(int(limit))
        try:
            with self._lock:
                rows = self._database.connection.execute(sql, params).fetchall()
        except sqlite3.DatabaseError as exc:
            raise DatabaseError(f"History query failed: {exc}") from exc
        return [MetricRow.from_row(row) for row in rows]

    def aggregate(
        self, start_ts: float, end_ts: float, bucket_seconds: int
    ) -> list[MetricRow]:
        """Average metrics into fixed time buckets for compact charts."""
        bucket = max(1, int(bucket_seconds))
        averages = ", ".join(f"AVG({column}) AS {column}" for column in NUMERIC_COLUMNS)
        sql = (
            f"SELECT CAST(ts / {bucket} AS INTEGER) * {bucket} AS ts, {averages} "
            "FROM metrics WHERE ts >= ? AND ts <= ? "
            f"GROUP BY CAST(ts / {bucket} AS INTEGER) * {bucket} ORDER BY ts ASC"
        )
        try:
            with self._lock:
                rows = self._database.connection.execute(
                    sql, (float(start_ts), float(end_ts))
                ).fetchall()
        except sqlite3.DatabaseError as exc:
            raise DatabaseError(f"History aggregation failed: {exc}") from exc
        return [MetricRow.from_row(row) for row in rows]

    def storage_stats(self) -> StorageStats:
        with self._lock:
            row = self._database.connection.execute(
                "SELECT COUNT(*), MIN(ts), MAX(ts) FROM metrics"
            ).fetchone()
        try:
            size = self._database.path.stat().st_size
        except OSError:
            size = 0
        try:
            size += self._database.path.with_name(self._database.path.name + "-wal").stat().st_size
        except OSError:
            pass
        return StorageStats(
            rows=int(row[0]) if row else 0,
            oldest_ts=float(row[1]) if row and row[1] is not None else None,
            newest_ts=float(row[2]) if row and row[2] is not None else None,
            file_size_bytes=size,
        )

    # -- maintenance --------------------------------------------------------
    def prune_older_than(self, cutoff_ts: float) -> int:
        with self._lock:
            try:
                with self._database.connection as connection:
                    cursor = connection.execute("DELETE FROM metrics WHERE ts < ?", (cutoff_ts,))
                    connection.execute("PRAGMA optimize")
                return int(cursor.rowcount or 0)
            except sqlite3.DatabaseError as exc:
                raise DatabaseError(f"History cleanup failed: {exc}") from exc

    def delete_all_metrics(self) -> int:
        with self._lock:
            try:
                with self._database.connection as connection:
                    cursor = connection.execute("DELETE FROM metrics")
                return int(cursor.rowcount or 0)
            except sqlite3.DatabaseError as exc:
                raise DatabaseError(f"History deletion failed: {exc}") from exc

    # -- gaming sessions ----------------------------------------------------
    def save_gaming_session(
        self,
        started_at: float,
        ended_at: float,
        summary: Mapping[str, object],
        samples: Sequence[Mapping[str, float | None]],
    ) -> int:
        try:
            with self._lock:
                with self._database.connection as connection:
                    cursor = connection.execute(
                        "INSERT INTO gaming_sessions(started_at, ended_at, summary_json, samples_json) "
                        "VALUES (?, ?, ?, ?)",
                        (
                            started_at,
                            ended_at,
                            json.dumps(summary),
                            json.dumps(list(samples)),
                        ),
                    )
            return int(cursor.lastrowid or 0)
        except sqlite3.DatabaseError as exc:
            raise DatabaseError(f"Could not save gaming session: {exc}") from exc

    def list_gaming_sessions(self, limit: int = 25) -> list[GamingSessionRow]:
        try:
            with self._lock:
                rows = self._database.connection.execute(
                    "SELECT id, started_at, ended_at, summary_json, samples_json "
                    "FROM gaming_sessions ORDER BY started_at DESC LIMIT ?",
                    (max(1, int(limit)),),
                ).fetchall()
        except sqlite3.DatabaseError as exc:
            raise DatabaseError(f"Could not read gaming sessions: {exc}") from exc
        return [
            GamingSessionRow(
                id=int(row["id"]),
                started_at=float(row["started_at"]),
                ended_at=float(row["ended_at"]) if row["ended_at"] is not None else None,
                summary_json=row["summary_json"],
                samples_json=row["samples_json"],
            )
            for row in rows
        ]

    def delete_gaming_session(self, session_id: int) -> None:
        with self._lock:
            with self._database.connection as connection:
                connection.execute("DELETE FROM gaming_sessions WHERE id = ?", (session_id,))

    def delete_all_gaming_sessions(self) -> int:
        with self._lock:
            with self._database.connection as connection:
                cursor = connection.execute("DELETE FROM gaming_sessions")
            return int(cursor.rowcount or 0)

    # -- export -------------------------------------------------------------
    @staticmethod
    def to_csv(rows: Sequence[MetricRow]) -> str:
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(CSV_HEADER)
        for row in rows:
            from datetime import datetime

            stamp = datetime.fromtimestamp(row.ts).isoformat(timespec="seconds")
            values: list[object] = [stamp, round(row.ts, 3)]
            for column in NUMERIC_COLUMNS:
                value = getattr(row, column)
                values.append("" if value is None else value)
            writer.writerow(values)
        return buffer.getvalue()

    def close(self) -> None:
        self._database.close()
