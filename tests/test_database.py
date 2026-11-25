"""Tests for local SQLite history and retention behavior."""

from __future__ import annotations

from pathlib import Path

import pytest
import sqlite3

from nexus.database.connection import Database
from nexus.database.repository import HistoryRepository
from nexus.services.history_service import HistoryRecorder
from nexus.utils.exceptions import DatabaseError


def _record(timestamp: float, cpu: float | None) -> dict[str, float | int | None]:
    return {"ts": timestamp, "cpu_percent": cpu, "memory_percent": 40.0}


def test_database_initializes_schema_and_passes_integrity_check(tmp_path):
    database = Database(tmp_path / "nested" / "history.db")
    repository = HistoryRepository(database)

    assert database.path.exists()
    assert database.integrity_check() == (True, "ok")
    row = database.connection.execute(
        "SELECT value FROM meta WHERE key = 'schema_version'"
    ).fetchone()
    assert row[0] == "1"
    assert repository.count() == 0
    repository.close()


def test_insert_range_aggregation_and_retention(tmp_path):
    repository = HistoryRepository(Database(tmp_path / "history.db"))
    repository.insert_many(
        [_record(100.0, 20.0), _record(102.0, 40.0), _record(111.0, 60.0)]
    )

    rows = repository.query_range(100.0, 110.0, limit=1)
    assert len(rows) == 1
    assert rows[0].ts == 100.0
    assert rows[0].cpu_percent == 20.0

    buckets = repository.aggregate(100.0, 120.0, bucket_seconds=10)
    assert [(row.ts, row.cpu_percent) for row in buckets] == [
        (100.0, 30.0),
        (110.0, 60.0),
    ]

    assert repository.prune_older_than(102.0) == 1
    assert repository.count() == 2
    assert [row.ts for row in repository.query_range(0.0, 200.0)] == [102.0, 111.0]
    repository.close()


def test_storage_stats_include_database_and_wal_size(tmp_path):
    path = tmp_path / "history.db"
    repository = HistoryRepository(Database(path))
    repository.insert_many([_record(float(index), float(index)) for index in range(100)])

    stats = repository.storage_stats()
    wal_path = path.with_name(path.name + "-wal")
    expected_size = path.stat().st_size + (wal_path.stat().st_size if wal_path.exists() else 0)

    assert stats.rows == 100
    assert stats.oldest_ts == 0.0
    assert stats.newest_ts == 99.0
    assert stats.file_size_bytes == expected_size
    repository.close()


def test_in_memory_database_supports_history_queries():
    repository = HistoryRepository(Database(Path(":memory:")))
    repository.insert_metric(_record(5.0, None))

    row = repository.query_range(0.0, 10.0)[0]
    assert row.cpu_percent is None
    assert row.memory_percent == 40.0
    assert repository.storage_stats().rows == 1
    repository.close()


def test_recorder_prunes_according_to_configured_retention(tmp_path, monkeypatch):
    repository = HistoryRepository(Database(tmp_path / "history.db"))
    repository.insert_many(
        [_record(100_000.0, 1.0), _record(110_000.0, 2.0), _record(200_000.0, 3.0)]
    )
    recorder = HistoryRecorder(repository, retention_days=1)
    monkeypatch.setattr("nexus.services.history_service.time.time", lambda: 200_000.0)

    recorder._prune()

    remaining = repository.query_range(0.0, 300_000.0)
    assert [row.ts for row in remaining] == [200_000.0]
    repository.close()


def test_database_initialization_error_is_mapped(tmp_path):
    parent_file = tmp_path / "not-a-directory"
    parent_file.write_text("occupied", encoding="utf-8")

    with pytest.raises(DatabaseError, match="Filesystem error"):
        Database(parent_file / "history.db").connect()


def test_unversioned_history_is_backed_up_and_migrated_without_data_loss(tmp_path):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE metrics (id INTEGER PRIMARY KEY, ts REAL NOT NULL, cpu_percent REAL)"
        )
        connection.execute("INSERT INTO metrics(ts, cpu_percent) VALUES(123.0, 42.0)")

    database = Database(path)
    database.connect()
    assert database.connection.execute(
        "SELECT ts, cpu_percent FROM metrics"
    ).fetchone()[:] == (123.0, 42.0)
    assert database.connection.execute(
        "SELECT value FROM meta WHERE key='schema_version'"
    ).fetchone()[0] == "1"
    backups = list(tmp_path.glob("legacy.pre-migration-v0-*.db"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as backup:
        assert backup.execute("SELECT cpu_percent FROM metrics").fetchone()[0] == 42.0
    database.close()


def test_newer_database_schema_is_rejected_without_erasing_rows(tmp_path):
    path = tmp_path / "future.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("INSERT INTO meta(key, value) VALUES('schema_version', '99')")
        connection.execute("CREATE TABLE keep_me (value TEXT)")
        connection.execute("INSERT INTO keep_me(value) VALUES('preserved')")

    with pytest.raises(DatabaseError, match="newer than supported"):
        Database(path).connect()
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT value FROM keep_me").fetchone()[0] == "preserved"
