from __future__ import annotations

from pathlib import Path

from nexus.utils import paths


def test_macos_paths_follow_library_conventions(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(paths.sys, "platform", "darwin")
    monkeypatch.setattr(paths.Path, "home", lambda: tmp_path)
    monkeypatch.delenv("NEXUS_DATA_DIR", raising=False)
    monkeypatch.delenv("NEXUS_CACHE_DIR", raising=False)

    assert paths.app_data_dir() == tmp_path / "Library" / "Application Support" / "NEXUS"
    assert paths.logs_dir() == tmp_path / "Library" / "Logs" / "NEXUS"
    assert paths.cache_dir() == tmp_path / "Library" / "Caches" / "NEXUS"
    assert paths.database_path().parent == paths.app_data_dir()
    assert paths.settings_path().parent == paths.app_data_dir()


def test_test_data_override_is_preserved(monkeypatch, tmp_path: Path) -> None:
    override = tmp_path / "isolated"
    monkeypatch.setattr(paths.sys, "platform", "darwin")
    monkeypatch.setenv("NEXUS_DATA_DIR", str(override))
    monkeypatch.delenv("NEXUS_CACHE_DIR", raising=False)

    assert paths.app_data_dir() == override
    assert paths.logs_dir() == override / "logs"
