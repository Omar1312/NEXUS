from __future__ import annotations

import os
from pathlib import Path

import pytest

from nexus.core.storage_scanner import StorageScanner


def test_scan_reports_totals_categories_and_largest_entries(tmp_path: Path) -> None:
    (tmp_path / "nested").mkdir()
    (tmp_path / "small.txt").write_bytes(b"abc")
    (tmp_path / "nested" / "large.mp4").write_bytes(b"12345")

    result = StorageScanner().scan(tmp_path)

    assert result.total_bytes == 8
    assert result.total_files == 2
    assert result.total_directories == 2
    assert {item.name: (item.bytes, item.files) for item in result.categories} == {
        "Documents": (3, 1), "Video": (5, 1)
    }
    assert result.largest_files[0].size == 5
    assert any(item.path.endswith("nested") and item.size == 5 for item in result.largest_directories)


def test_entry_budget_truncates_without_buffering_whole_tree(tmp_path: Path) -> None:
    for index in range(20):
        (tmp_path / f"{index:02}.dat").write_bytes(b"x")

    result = StorageScanner(max_entries=4).scan(tmp_path)

    assert result.truncated
    assert result.total_files <= 4
    assert result.total_bytes <= 4


def test_cancelled_scan_marks_partial_counts_and_discards_aggregates(tmp_path: Path) -> None:
    (tmp_path / "child").mkdir()
    (tmp_path / "first.dat").write_bytes(b"123")
    (tmp_path / "child" / "later.dat").write_bytes(b"4567")
    progress = []

    # Trigger cancellation from the progress callback after the root is read.
    import threading

    cancel = threading.Event()
    progress.append(lambda _item: cancel.set())
    result = StorageScanner(
        cancel_event=cancel,
        progress_callback=progress[0],
        progress_interval=0,
    ).scan(tmp_path)

    assert result.cancelled
    assert result.largest_files == ()
    assert result.largest_directories == ()
    assert result.categories == ()


def test_cancel_before_scan_returns_cancelled_result(tmp_path: Path) -> None:
    import threading

    cancel = threading.Event()
    cancel.set()
    result = StorageScanner(cancel_event=cancel).scan(tmp_path)
    assert result.cancelled
    assert result.total_files == 0
    assert not result.largest_files


def test_access_denied_scandir_is_reported_and_scan_continues(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "denied").mkdir()
    (tmp_path / "visible.txt").write_text("ok")
    original_scandir = os.scandir

    def guarded_scandir(path):
        if os.fspath(path).endswith("denied"):
            raise PermissionError("denied")
        return original_scandir(path)

    monkeypatch.setattr("nexus.core.storage_scanner.os.scandir", guarded_scandir)
    result = StorageScanner().scan(tmp_path)
    assert result.total_files == 1
    assert any("access denied" in error for error in result.errors)


def test_root_symlink_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation is unavailable in this environment")
    with pytest.raises(ValueError, match="symbolic link"):
        StorageScanner().scan(link)


def test_entry_symlink_is_skipped(tmp_path: Path) -> None:
    scan_root = tmp_path / "root"
    scan_root.mkdir()
    target = tmp_path / "outside"
    target.mkdir()
    (target / "large.bin").write_bytes(b"outside")
    link = scan_root / "link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation is unavailable in this environment")
    result = StorageScanner().scan(scan_root)
    assert result.total_files == 0
    assert result.skipped_links == 1
