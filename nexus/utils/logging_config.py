"""Structured logging for NEXUS.

Logs are written to a rotating file in the application data directory and, when
running from source, to stderr. The log level is controlled by the user through
Settings and can be changed at runtime without restarting.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

from nexus.utils.paths import logs_dir

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_configured = False


class _SafeRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """Rotating handler that never crashes the app if the log file is locked."""

    def handleError(self, record: logging.LogRecord) -> None:  # noqa: N802
        if sys.stderr:
            try:
                sys.stderr.write(f"logging error for {record.name}\n")
            except Exception:  # pragma: no cover - best effort
                pass


def configure_logging(level: str | int = "INFO", *, log_file: Path | None = None) -> Path:
    """Configure root logging once and return the active log file path."""
    global _configured
    resolved = logging.getLevelName(str(level).upper()) if isinstance(level, str) else level
    if not isinstance(resolved, int):
        resolved = logging.INFO

    root = logging.getLogger()
    root.setLevel(resolved)

    if _configured:
        for handler in root.handlers:
            handler.setLevel(resolved)
        return log_file or logs_dir() / "nexus.log"

    target = log_file or logs_dir() / "nexus.log"
    target.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")

    file_handler = _SafeRotatingFileHandler(
        target, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(resolved)
    root.addHandler(file_handler)

    if sys.stderr is not None:
        console = logging.StreamHandler(stream=sys.stderr)
        console.setFormatter(formatter)
        console.setLevel(max(resolved, logging.WARNING))
        root.addHandler(console)

    logging.getLogger("PySide6").setLevel(logging.WARNING)
    _configured = True
    logging.getLogger(__name__).info("Logging initialised at %s (file=%s)", resolved, target)
    return target


def set_log_level(level: str | int) -> None:
    resolved = logging.getLevelName(str(level).upper()) if isinstance(level, str) else level
    if not isinstance(resolved, int):
        return
    root = logging.getLogger()
    root.setLevel(resolved)
    for handler in root.handlers:
        # Console handler stays at WARNING or above to avoid noisy terminals.
        if isinstance(handler, logging.StreamHandler) and not isinstance(
            handler, logging.handlers.RotatingFileHandler
        ):
            handler.setLevel(max(resolved, logging.WARNING))
        else:
            handler.setLevel(resolved)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
