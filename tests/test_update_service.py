from __future__ import annotations

import hashlib
import json
from pathlib import Path
import threading
import urllib.error

import pytest

from nexus.services import update_service as updates


def _release(version: str, *, prerelease: bool = False) -> dict:
    return {
        "tag_name": f"v{version}",
        "name": f"NEXUS {version}",
        "body": "Release notes",
        "draft": False,
        "prerelease": prerelease,
        "html_url": "https://github.com/org/repo/releases/tag/v" + version,
        "assets": [
            {
                "name": f"NEXUS-Setup-{version}-x64.exe",
                "browser_download_url": "https://github.com/org/repo/releases/download/setup.exe",
                "size": 10,
            },
            {
                "name": "SHA256SUMS.txt",
                "browser_download_url": "https://github.com/org/repo/releases/download/SHA256SUMS.txt",
                "size": 100,
            },
        ],
    }


def test_unconfigured_repository_is_explicit(monkeypatch):
    monkeypatch.delenv("NEXUS_RELEASE_REPOSITORY", raising=False)
    with pytest.raises(updates.UpdateError, match="not configured"):
        updates.check_latest_release()


def test_semantic_comparison_and_expected_assets(monkeypatch):
    monkeypatch.setattr(updates, "platform_id", lambda: "windows")
    monkeypatch.setenv("NEXUS_RELEASE_REPOSITORY", "nexus/project")
    monkeypatch.setattr(updates, "_request_json", lambda _url: _release("1.10.0"))
    release = updates.check_latest_release()
    assert release is not None
    assert release.version == "1.10.0"
    assert release.installer_name == "NEXUS-Setup-1.10.0-x64.exe"


@pytest.mark.parametrize("version", ["1.0.0-rc.1", "0.9.0"])
def test_equal_or_older_release_is_not_offered(monkeypatch, version):
    monkeypatch.setenv("NEXUS_RELEASE_REPOSITORY", "nexus/project")
    monkeypatch.setattr(updates, "_request_json", lambda _url: _release(version))
    assert updates.check_latest_release() is None


def test_invalid_semver_release_is_ignored(monkeypatch):
    monkeypatch.setenv("NEXUS_RELEASE_REPOSITORY", "nexus/project")
    monkeypatch.setattr(updates, "_request_json", lambda _url: _release("1.2"))
    assert updates.check_latest_release() is None


def test_prerelease_is_opt_in_and_compared_semantically(monkeypatch):
    monkeypatch.setattr(updates, "platform_id", lambda: "windows")
    monkeypatch.setenv("NEXUS_RELEASE_REPOSITORY", "nexus/project")
    prerelease = [_release("1.3.0-rc.1", prerelease=True)]
    monkeypatch.setattr(updates, "_request_json", lambda _url: prerelease)
    assert updates.check_latest_release() is None
    releases = [_release("1.3.0-rc.1", prerelease=True), _release("1.2.0")]
    monkeypatch.setattr(updates, "_request_json", lambda _url: releases)
    selected = updates.check_latest_release(allow_prerelease=True)
    assert selected is not None and selected.version == "1.3.0-rc.1"
    assert selected.installer_name == "NEXUS-Setup-1.3.0-rc.1-x64.exe"



def test_macos_updates_select_exact_architecture_dmg(monkeypatch):
    monkeypatch.setenv("NEXUS_RELEASE_REPOSITORY", "nexus/project")
    monkeypatch.setattr(updates, "platform_id", lambda: "macos")
    monkeypatch.setattr(updates, "architecture_id", lambda: "arm64")
    data = _release("1.10.0")
    data["assets"][0]["name"] = "NEXUS-1.10.0-macos-arm64.dmg"
    monkeypatch.setattr(updates, "_request_json", lambda _url: data)
    release = updates.check_latest_release()
    assert release is not None
    assert release.installer_name == "NEXUS-1.10.0-macos-arm64.dmg"

    monkeypatch.setattr(updates, "architecture_id", lambda: "x64")
    with pytest.raises(updates.UpdateError, match="missing the expected"):
        updates.check_latest_release()


def test_mac_dmg_is_never_launched_as_an_installer(tmp_path, monkeypatch):
    folder = tmp_path / "NEXUS-updates"
    folder.mkdir()
    dmg = folder / "NEXUS-1.1.0-macos-arm64.dmg"
    dmg.write_bytes(b"dmg")
    monkeypatch.setattr(updates, "platform_id", lambda: "macos")
    with pytest.raises(updates.UpdateError, match="only on Windows"):
        updates.launch_installer(dmg)


def test_missing_expected_assets_is_rejected(monkeypatch):
    monkeypatch.setenv("NEXUS_RELEASE_REPOSITORY", "nexus/project")
    data = _release("1.1.0")
    data["assets"] = []
    monkeypatch.setattr(updates, "_request_json", lambda _url: data)
    with pytest.raises(updates.UpdateError, match="missing the expected"):
        updates.check_latest_release()


def test_network_timeout_is_reported_without_an_api_token(monkeypatch):
    monkeypatch.setenv("NEXUS_RELEASE_REPOSITORY", "nexus/project")

    def timeout(*_args, **_kwargs):
        raise urllib.error.URLError("timed out")

    monkeypatch.setattr(updates.urllib.request, "urlopen", timeout)
    with pytest.raises(updates.UpdateError, match="Could not check for updates"):
        updates.check_latest_release()


def test_verified_download_requires_matching_checksum(tmp_path: Path, monkeypatch):
    installer_data = b"safe test payload"
    release = updates.ReleaseInfo(
        version="1.1.0",
        name="NEXUS 1.1.0",
        notes="notes",
        installer_url="https://github.com/org/repo/NEXUS.exe",
        installer_name="NEXUS-Setup-1.1.0-x64.exe",
        installer_size=len(installer_data),
        checksum_url="https://github.com/org/repo/SHA256SUMS.txt",
        html_url="https://github.com/org/repo/releases/tag/v1.1.0",
    )
    monkeypatch.setattr(updates.tempfile, "gettempdir", lambda: str(tmp_path))

    def fake_download(url, destination, *, limit, cancel_event=None):
        if "SHA256SUMS" in url:
            text = hashlib.sha256(installer_data).hexdigest() + "  " + release.installer_name + "\n"
            destination.write_text(text, encoding="utf-8")
            return hashlib.sha256(text.encode()).digest()
        destination.write_bytes(installer_data)
        return hashlib.sha256(installer_data).digest()

    monkeypatch.setattr(updates, "_download", fake_download)
    result = updates.download_verified_installer(release)
    assert result.read_bytes() == installer_data

    def bad_download(url, destination, *, limit, cancel_event=None):
        if "SHA256SUMS" in url:
            destination.write_text("0" * 64 + "  " + release.installer_name, encoding="utf-8")
            return b""
        destination.write_bytes(installer_data)
        return hashlib.sha256(installer_data).digest()

    monkeypatch.setattr(updates, "_download", bad_download)
    with pytest.raises(updates.UpdateError, match="SHA-256 verification failed"):
        updates.download_verified_installer(release)
    assert not result.exists()


def test_cancelled_download_removes_partial_installer(tmp_path: Path, monkeypatch):
    release = updates.ReleaseInfo(
        version="1.1.0", name="NEXUS", notes="", installer_url="https://github.com/a/b/file.exe",
        installer_name="NEXUS-Setup-1.1.0-x64.exe", installer_size=None,
        checksum_url="https://github.com/a/b/SHA256SUMS.txt", html_url="",
    )
    monkeypatch.setattr(updates.tempfile, "gettempdir", lambda: str(tmp_path))
    cancel = threading.Event()

    def interrupted(_url, destination, *, limit, cancel_event=None):
        destination.write_bytes(b"partial")
        cancel.set()
        raise updates.UpdateError("Download cancelled.")

    monkeypatch.setattr(updates, "_download", interrupted)
    with pytest.raises(updates.UpdateError, match="cancelled"):
        updates.download_verified_installer(release, cancel_event=cancel)
    assert not (tmp_path / "NEXUS-updates" / release.installer_name).exists()


def test_installer_handoff_only_accepts_verified_update_folder(tmp_path: Path, monkeypatch):
    folder = tmp_path / "NEXUS-updates"
    folder.mkdir()
    installer = folder / "NEXUS-Setup-1.1.0-x64.exe"
    installer.write_bytes(b"test")
    launched = []
    monkeypatch.setattr(updates.sys, "platform", "win32")
    monkeypatch.setattr(updates.subprocess, "Popen", lambda args, **kwargs: launched.append(args))

    updates.launch_installer(installer)
    assert launched == [[str(installer.resolve())]]
    outside = tmp_path / "other.exe"
    outside.write_bytes(b"not an installer")
    with pytest.raises(updates.UpdateError, match="unexpected installer path"):
        updates.launch_installer(outside)


def test_settings_add_update_preferences_without_resetting_old_preferences(tmp_path: Path):
    from nexus.services.settings_service import SettingsService

    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"theme": "light", "refresh_interval_s": 5}), encoding="utf-8")
    settings = SettingsService(path)
    assert settings.current.theme == "light"
    assert settings.current.refresh_interval_s == 5
    assert settings.current.auto_update_checks is False
    assert settings.current.include_prereleases is False
    settings.update(
        auto_update_checks=True,
        include_prereleases=True,
        last_update_check="2026-11-24 12:00",
    )
    restored = SettingsService(path)
    assert restored.current.theme == "light"
    assert restored.current.auto_update_checks is True
    assert restored.current.include_prereleases is True
    assert restored.current.last_update_check == "2026-11-24 12:00"
