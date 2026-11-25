"""Background-friendly folder size scanner.

Safety properties:

* Read-only. NEXUS never deletes or moves files from this module.
* Symbolic links, junctions and other reparse points are skipped, never
  followed, and duplicated physical directories are detected via ``(st_dev,
  st_ino)`` so junction loops cannot cause infinite traversal.
* Permission errors are collected per entry and reported to the user.
* Cancellation is checked frequently; partial results are discarded.
"""

from __future__ import annotations

import csv
import heapq
import io
import json
import logging
import os
import stat
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable

log = logging.getLogger(__name__)

CATEGORY_MAP: dict[str, str] = {
    "Video": {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm", ".flv", ".m4v"},
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tif", ".tiff", ".heic", ".raw"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"},
    "Documents": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".md", ".rtf", ".odt"},
    "Archives": {".zip", ".7z", ".rar", ".tar", ".gz", ".bz2", ".xz", ".iso"},
    "Code": {".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".json", ".xml", ".c", ".cpp", ".h", ".cs", ".java", ".rs", ".go"},
    "Executables": {".exe", ".dll", ".msi", ".sys", ".so", ".bin"},
    "Databases": {".db", ".sqlite", ".mdb", ".bak"},
}
_EXTENSION_LOOKUP = {
    extension: category for category, extensions in CATEGORY_MAP.items() for extension in extensions
}

_SYSTEM_FOLDER_NAMES = {
    "$recycle.bin",
    "system volume information",
    "recovery",
    "config.msi",
    "$windows.~bt",
    "$windows.~ws",
}

FILE_ATTRIBUTE_REPARSE_POINT = 0x400


@dataclass(frozen=True, slots=True)
class FileRecord:
    path: str
    size: int


@dataclass(frozen=True, slots=True)
class DirectoryRecord:
    path: str
    size: int


@dataclass(frozen=True, slots=True)
class CategoryUsage:
    name: str
    bytes: int
    files: int


@dataclass(frozen=True, slots=True)
class ScanProgress:
    files: int
    directories: int
    bytes: int
    current_path: str


@dataclass(frozen=True, slots=True)
class ScanResult:
    root: str
    total_bytes: int
    total_files: int
    total_directories: int
    largest_files: tuple[FileRecord, ...]
    largest_directories: tuple[DirectoryRecord, ...]
    categories: tuple[CategoryUsage, ...]
    errors: tuple[str, ...]
    skipped_links: int
    skipped_system_dirs: int
    duration_seconds: float
    scanned_at: float
    cancelled: bool = False
    truncated: bool = False

    @property
    def error_count(self) -> int:
        return len(self.errors)

    def to_csv(self) -> str:
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(["NEXUS storage scan", self.root])
        writer.writerow(["Scanned at", datetime.fromtimestamp(self.scanned_at).isoformat(timespec="seconds")])
        writer.writerow(["Total size (bytes)", self.total_bytes])
        writer.writerow(["Files", self.total_files])
        writer.writerow(["Directories", self.total_directories])
        writer.writerow([])
        writer.writerow(["Largest files", "bytes"])
        for record in self.largest_files:
            writer.writerow([record.path, record.size])
        writer.writerow([])
        writer.writerow(["Largest directories", "bytes"])
        for record in self.largest_directories:
            writer.writerow([record.path, record.size])
        writer.writerow([])
        writer.writerow(["Category", "bytes", "files"])
        for category in self.categories:
            writer.writerow([category.name, category.bytes, category.files])
        writer.writerow([])
        writer.writerow(["Errors"])
        for error in self.errors:
            writer.writerow([error])
        return buffer.getvalue()

    def to_json(self) -> str:
        return json.dumps(
            {
                "root": self.root,
                "scanned_at": self.scanned_at,
                "total_bytes": self.total_bytes,
                "total_files": self.total_files,
                "total_directories": self.total_directories,
                "duration_seconds": round(self.duration_seconds, 2),
                "largest_files": [{"path": r.path, "size": r.size} for r in self.largest_files],
                "largest_directories": [
                    {"path": r.path, "size": r.size} for r in self.largest_directories
                ],
                "categories": [
                    {"name": c.name, "bytes": c.bytes, "files": c.files} for c in self.categories
                ],
                "errors": list(self.errors),
                "skipped_links": self.skipped_links,
                "skipped_system_dirs": self.skipped_system_dirs,
                "truncated": self.truncated,
            },
            indent=2,
        )


def category_for(extension: str) -> str:
    return _EXTENSION_LOOKUP.get(extension.lower(), "Other")


class StorageScanner:
    """Scans a directory tree, reporting progress and honouring cancellation."""

    def __init__(
        self,
        *,
        top_files: int = 50,
        top_directories: int = 50,
        cancel_event: threading.Event | None = None,
        progress_callback: Callable[[ScanProgress], None] | None = None,
        skip_system_folders: bool = True,
        max_entries: int = 2_000_000,
        progress_interval: float = 0.25,
    ) -> None:
        self._top_files = max(1, top_files)
        self._top_directories = max(1, top_directories)
        self._cancel = cancel_event or threading.Event()
        self._progress = progress_callback
        self._skip_system = skip_system_folders
        self._max_entries = max(1, int(max_entries))
        self._progress_interval = progress_interval

    def scan(self, root: str | Path) -> ScanResult:
        started = time.perf_counter()
        root_path = Path(root)
        if not root_path.exists():
            raise FileNotFoundError(f"Folder not found: {root_path}")
        root_stat = os.stat(root_path, follow_symlinks=False)
        root_attributes = getattr(root_stat, "st_file_attributes", 0)
        if stat.S_ISLNK(root_stat.st_mode) or root_attributes & FILE_ATTRIBUTE_REPARSE_POINT:
            raise ValueError("Choose a regular folder, not a symbolic link or reparse point.")
        if not stat.S_ISDIR(root_stat.st_mode):
            raise NotADirectoryError(f"Not a folder: {root_path}")
        root_str = str(root_path)

        file_heap: list[tuple[int, str]] = []
        direct_sizes: dict[str, int] = {root_str: 0}
        parent_map: dict[str, str] = {}
        categories: dict[str, list[int]] = {}
        errors: list[str] = []
        visited: set[tuple[int, int]] = set()

        total_bytes = 0
        total_files = 0
        total_dirs = 0
        scanned_entries = 0
        skipped_links = 0
        skipped_system = 0
        truncated = False
        cancelled = False
        last_report = 0.0

        stack: list[str] = [root_str]
        while stack:
            if self._cancel.is_set():
                cancelled = True
                break
            if scanned_entries >= self._max_entries:
                truncated = True
                break
            current = stack.pop()
            try:
                dir_stat = os.stat(current, follow_symlinks=False)
                identity = (int(dir_stat.st_dev), int(dir_stat.st_ino))
                if identity in visited and identity != (0, 0):
                    skipped_links += 1
                    continue
                visited.add(identity)
            except OSError as exc:
                if len(errors) < 50:
                    errors.append(f"{current}: {exc}")
                continue

            try:
                entries = os.scandir(current)
            except PermissionError:
                if len(errors) < 50:
                    errors.append(f"{current}: access denied")
                continue
            except OSError as exc:
                if len(errors) < 50:
                    errors.append(f"{current}: {exc}")
                continue

            total_dirs += 1
            try:
                for entry in entries:
                    if self._cancel.is_set():
                        cancelled = True
                        break
                    if scanned_entries >= self._max_entries:
                        truncated = True
                        break
                    scanned_entries += 1
                    try:
                        if entry.is_symlink():
                            skipped_links += 1
                            continue
                        entry_stat = entry.stat(follow_symlinks=False)
                        attributes = getattr(entry_stat, "st_file_attributes", 0)
                        is_reparse = bool(attributes & FILE_ATTRIBUTE_REPARSE_POINT)
                        if entry.is_dir(follow_symlinks=False):
                            if is_reparse:
                                skipped_links += 1
                                continue
                            if self._skip_system and entry.name.lower() in _SYSTEM_FOLDER_NAMES:
                                skipped_system += 1
                                continue
                            child = entry.path
                            direct_sizes.setdefault(child, 0)
                            parent_map[child] = current
                            stack.append(child)
                            continue
                        if is_reparse:
                            skipped_links += 1
                            continue
                        if not entry.is_file(follow_symlinks=False):
                            continue
                        size = int(entry_stat.st_size)
                        total_files += 1
                        total_bytes += size
                        direct_sizes[current] = direct_sizes.get(current, 0) + size
                        extension = os.path.splitext(entry.name)[1]
                        bucket = categories.setdefault(category_for(extension), [0, 0])
                        bucket[0] += size
                        bucket[1] += 1
                        item = (size, entry.path)
                        if len(file_heap) < self._top_files:
                            heapq.heappush(file_heap, item)
                        elif size > file_heap[0][0]:
                            heapq.heapreplace(file_heap, item)
                    except PermissionError:
                        if len(errors) < 50:
                            errors.append(f"{entry.path}: access denied")
                    except OSError as exc:
                        if len(errors) < 50:
                            errors.append(f"{entry.path}: {exc}")
            except PermissionError:
                if len(errors) < 50:
                    errors.append(f"{current}: access denied")
            except OSError as exc:
                if len(errors) < 50:
                    errors.append(f"{current}: {exc}")
            finally:
                entries.close()

            if cancelled or truncated:
                break

            now = time.perf_counter()
            if self._progress and now - last_report >= self._progress_interval:
                last_report = now
                try:
                    self._progress(
                        ScanProgress(total_files, total_dirs, total_bytes, current)
                    )
                except Exception:  # pragma: no cover - UI callback must not break scan
                    log.debug("Progress callback failed", exc_info=True)

        if cancelled:
            return ScanResult(
                root=root_str,
                total_bytes=total_bytes,
                total_files=total_files,
                total_directories=total_dirs,
                largest_files=(),
                largest_directories=(),
                categories=(),
                errors=tuple(errors[:50]),
                skipped_links=skipped_links,
                skipped_system_dirs=skipped_system,
                duration_seconds=time.perf_counter() - started,
                scanned_at=time.time(),
                cancelled=True,
                truncated=truncated,
            )

        # Roll direct sizes up to every ancestor for accurate folder totals.
        dir_sizes = dict(direct_sizes)
        for directory in sorted(dir_sizes, key=len, reverse=True):
            parent = parent_map.get(directory)
            if parent is not None:
                dir_sizes[parent] = dir_sizes.get(parent, 0) + dir_sizes[directory]

        largest_directories = sorted(dir_sizes.items(), key=lambda item: item[1], reverse=True)
        largest_directories = [item for item in largest_directories if item[0] != root_str]
        top_dirs = tuple(
            DirectoryRecord(path, size) for path, size in largest_directories[: self._top_directories]
        )
        top_files = tuple(
            FileRecord(path, size) for size, path in sorted(file_heap, reverse=True)
        )
        category_records = tuple(
            CategoryUsage(name, value[0], value[1])
            for name, value in sorted(categories.items(), key=lambda item: item[1][0], reverse=True)
        )

        return ScanResult(
            root=root_str,
            total_bytes=total_bytes,
            total_files=total_files,
            total_directories=total_dirs,
            largest_files=top_files,
            largest_directories=top_dirs,
            categories=category_records,
            errors=tuple(errors[:50]),
            skipped_links=skipped_links,
            skipped_system_dirs=skipped_system,
            duration_seconds=time.perf_counter() - started,
            scanned_at=time.time(),
            cancelled=False,
            truncated=truncated,
        )


def format_scan_errors(errors: Iterable[str], limit: int = 10) -> str:
    items = list(errors)
    if not items:
        return "No access errors."
    head = "\n".join(items[:limit])
    remaining = len(items) - limit
    return head + (f"\n… and {remaining} more" if remaining > 0 else "")
