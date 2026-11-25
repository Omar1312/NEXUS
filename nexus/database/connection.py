"""Database connection and schema management (SQLite, WAL mode)."""

from __future__ import annotations

import logging
import sqlite3
import time
from pathlib import Path

from nexus.utils.exceptions import DatabaseError
from nexus.utils.paths import database_path

log = logging.getLogger(__name__)

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    cpu_percent REAL,
    cpu_temp_c REAL,
    memory_percent REAL,
    memory_used_bytes INTEGER,
    disk_read_bps REAL,
    disk_write_bps REAL,
    disk_activity_percent REAL,
    net_down_bps REAL,
    net_up_bps REAL,
    gpu_percent REAL,
    gpu_mem_percent REAL,
    gpu_temp_c REAL,
    score REAL
);
CREATE INDEX IF NOT EXISTS idx_metrics_ts ON metrics(ts);

CREATE TABLE IF NOT EXISTS gaming_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at REAL NOT NULL,
    ended_at REAL,
    summary_json TEXT,
    samples_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_gaming_started ON gaming_sessions(started_at);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

_MIGRATIONS: dict[int, tuple[str, ...]] = {
    1: tuple(statement.strip() for statement in _SCHEMA.split(";") if statement.strip()),
}


class Database:
    """Owns a single SQLite connection with explicit lifecycle and error mapping.

    SQLite objects are not used from multiple threads here except through the
    repository's lock-protected writer, so ``check_same_thread=False`` is safe.
    """

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or database_path()
        self._preexisting_nonempty = False
        if str(self.path) != ":memory:":
            try:
                self._preexisting_nonempty = self.path.exists() and self.path.stat().st_size > 0
            except OSError:
                pass
        self._connection: sqlite3.Connection | None = None

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise DatabaseError("Database is not connected.")
        return self._connection

    def connect(self) -> sqlite3.Connection:
        if self._connection is not None:
            return self._connection
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(
                str(self.path), timeout=8.0, check_same_thread=False
            )
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=NORMAL")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=5000")
            self._connection = connection
            try:
                self._initialize()
            except Exception:
                self._connection = None
                connection.close()
                raise
        except sqlite3.DatabaseError as exc:
            raise DatabaseError(
                f"SQLite could not open {self.path}: {exc}",
                user_message="The performance history database could not be opened.",
            ) from exc
        except OSError as exc:
            raise DatabaseError(
                f"Filesystem error for {self.path}: {exc}",
                user_message="The performance history folder is not writable.",
            ) from exc
        return self._connection

    def _initialize(self) -> None:
        connection = self.connection
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "meta" in tables:
            row = connection.execute(
                "SELECT value FROM meta WHERE key='schema_version'"
            ).fetchone()
            try:
                current_version = int(row[0]) if row else 0
            except (TypeError, ValueError) as exc:
                raise DatabaseError("SQLite schema version metadata is invalid.") from exc
        else:
            current_version = 0
        if current_version > SCHEMA_VERSION:
            raise DatabaseError(
                f"Database schema {current_version} is newer than supported schema {SCHEMA_VERSION}; "
                "this version cannot safely open it."
            )
        if current_version < SCHEMA_VERSION and self._preexisting_nonempty:
            self._backup_before_migration(connection, current_version)

        try:
            connection.execute("BEGIN IMMEDIATE")
            for target_version in range(current_version + 1, SCHEMA_VERSION + 1):
                statements = _MIGRATIONS.get(target_version)
                if statements is None:
                    raise DatabaseError(f"No database migration is defined for version {target_version}.")
                for statement in statements:
                    connection.execute(statement)
            connection.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        log.debug("Database ready at %s", self.path)

    def _backup_before_migration(self, connection: sqlite3.Connection, old_version: int) -> Path:
        """Write an SQLite-consistent backup before applying a schema migration."""
        backup_path = self.path.with_name(
            f"{self.path.stem}.pre-migration-v{old_version}-{time.time_ns()}{self.path.suffix or '.db'}"
        )
        try:
            with sqlite3.connect(str(backup_path)) as backup:
                connection.backup(backup)
        except sqlite3.DatabaseError as exc:
            backup_path.unlink(missing_ok=True)
            raise DatabaseError(
                f"Could not create pre-migration backup {backup_path}: {exc}",
                user_message="NEXUS could not safely back up history before updating its database.",
            ) from exc
        log.info("Created database migration backup at %s", backup_path)
        return backup_path

    def integrity_check(self) -> tuple[bool, str]:
        """Run SQLite's integrity check; used at startup and by tests."""
        try:
            row = self.connection.execute("PRAGMA quick_check").fetchone()
            ok = bool(row) and str(row[0]).lower() == "ok"
            return ok, str(row[0]) if row else "no result"
        except sqlite3.DatabaseError as exc:
            return False, str(exc)

    def close(self) -> None:
        if self._connection is not None:
            try:
                self._connection.commit()
                self._connection.close()
            except sqlite3.Error as exc:  # pragma: no cover - shutdown path
                log.debug("Error while closing database: %s", exc)
            finally:
                self._connection = None
