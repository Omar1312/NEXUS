"""Opt-in GitHub Releases discovery and verified installer downloads.

Checks are disabled until ``NEXUS_RELEASE_REPOSITORY=owner/repo`` is configured.
SHA-256 protects against incomplete or mismatched downloads; it does not
authenticate the publisher. A trusted signed release remains necessary for
strong publisher authentication.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from packaging.version import InvalidVersion, Version

from nexus import __version__
from nexus.utils.paths import project_root
from nexus.platforms.selection import architecture_id, platform_id

API_ROOT = "https://api.github.com/repos/"
TIMEOUT_SECONDS = 15
MAX_INSTALLER_BYTES = 500 * 1024 * 1024
_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z.-]+))?(?:\+([0-9A-Za-z.-]+))?$"
)


class UpdateError(RuntimeError):
    """Expected update discovery, validation, or download failure."""


@dataclass(frozen=True, slots=True)
class ReleaseInfo:
    version: str
    name: str
    notes: str
    installer_url: str
    installer_name: str
    installer_size: int | None
    checksum_url: str
    html_url: str


def current_version() -> Version:
    return Version(__version__)


def configured_repository() -> str | None:
    value = os.environ.get("NEXUS_RELEASE_REPOSITORY", "").strip()
    if not value:
        config_path = project_root() / "assets" / "update_config.json"
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            if not isinstance(config, dict):
                raise UpdateError("The update source configuration must be a JSON object.")
            value = str(config.get("repository") or "").strip()
        except FileNotFoundError:
            value = ""
        except (OSError, json.JSONDecodeError) as exc:
            raise UpdateError(f"The configured update source could not be read: {exc}") from exc
    if not value:
        return None
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
        raise UpdateError("NEXUS_RELEASE_REPOSITORY must be in owner/repository format.")
    return value


def _request_json(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "NEXUS-Update-Check"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read(2_000_000).decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 403 and exc.headers.get("X-RateLimit-Remaining") == "0":
            raise UpdateError("GitHub API rate limit reached. Try again later.") from exc
        raise UpdateError(f"Release service returned HTTP {exc.code}.") from exc
    except (urllib.error.URLError, TimeoutError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise UpdateError(f"Could not check for updates: {exc}") from exc


def check_latest_release(*, allow_prerelease: bool = False) -> ReleaseInfo | None:
    """Return a newer stable release, or ``None`` if already current."""
    repository = configured_repository()
    if repository is None:
        raise UpdateError("Updates are not configured for this build.")
    endpoint = "releases?per_page=20" if allow_prerelease else "releases/latest"
    response = _request_json(API_ROOT + repository + "/" + endpoint)
    candidates = response if isinstance(response, list) else [response]
    valid = []
    for payload in candidates:
        if not isinstance(payload, dict) or payload.get("draft"):
            continue
        if payload.get("prerelease") and not allow_prerelease:
            continue
        tag = str(payload.get("tag_name", ""))
        raw_version = tag[1:] if tag.lower().startswith("v") else tag
        if not _SEMVER_RE.fullmatch(raw_version):
            continue
        try:
            valid.append((Version(raw_version), raw_version, payload))
        except InvalidVersion:
            continue
    newer = [item for item in valid if item[0] > current_version()]
    if not newer:
        return None
    _, latest, payload = max(newer, key=lambda item: item[0])
    assets = payload.get("assets")
    if not isinstance(assets, list):
        raise UpdateError("Release metadata does not contain a valid asset list.")
    installer = None
    checksum = None
    if platform_id() == "macos":
        expected_name = f"NEXUS-{latest}-macos-{architecture_id()}.dmg"
    else:
        expected_name = f"NEXUS-Setup-{latest}-x64.exe"
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = asset.get("name")
        url = asset.get("browser_download_url")
        if not isinstance(url, str) or urllib.parse.urlparse(url).scheme != "https":
            continue
        if name == expected_name:
            installer = asset
        elif name == "SHA256SUMS.txt":
            checksum = asset
    if installer is None or checksum is None:
        raise UpdateError(f"Release {latest} is missing the expected installer or SHA256SUMS.txt.")
    size = installer.get("size")
    if size is not None and (not isinstance(size, int) or size <= 0 or size > MAX_INSTALLER_BYTES):
        raise UpdateError("Installer metadata reports an invalid or excessive file size.")
    return ReleaseInfo(
        version=str(latest),
        name=str(payload.get("name") or f"NEXUS {latest}"),
        notes=str(payload.get("body") or "No release notes were provided."),
        installer_url=installer["browser_download_url"],
        installer_name=expected_name,
        installer_size=size,
        checksum_url=checksum["browser_download_url"],
        html_url=str(payload.get("html_url") or ""),
    )


def _download(url: str, destination: Path, *, limit: int, cancel_event=None) -> bytes:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in {
        "github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com"
    }:
        raise UpdateError("Release assets must be downloaded from GitHub over HTTPS.")
    request = urllib.request.Request(url, headers={"User-Agent": "NEXUS-Update-Check"})
    digest = hashlib.sha256()
    count = 0
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            final = urllib.parse.urlparse(response.geturl())
            if final.scheme != "https" or final.hostname not in {
                "github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com"
            }:
                raise UpdateError("GitHub redirected the download to an untrusted host.")
            with destination.open("wb") as stream:
                while True:
                    if cancel_event is not None and cancel_event.is_set():
                        raise UpdateError("Download cancelled.")
                    block = response.read(1024 * 128)
                    if not block:
                        break
                    count += len(block)
                    if count > limit:
                        raise UpdateError("Downloaded file exceeds its allowed size.")
                    digest.update(block)
                    stream.write(block)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    if count == 0:
        destination.unlink(missing_ok=True)
        raise UpdateError("The downloaded file was empty.")
    return digest.digest()


def download_verified_installer(release: ReleaseInfo, *, cancel_event=None) -> Path:
    """Download an installer to a private temp folder and verify its SHA-256."""
    if cancel_event is not None and cancel_event.is_set():
        raise UpdateError("Download cancelled.")
    root = Path(tempfile.gettempdir()) / "NEXUS-updates"
    root.mkdir(parents=True, exist_ok=True)
    installer_path = root / release.installer_name
    checksum_path = root / "SHA256SUMS.txt"
    try:
        expected_size = release.installer_size or MAX_INSTALLER_BYTES
        digest = _download(
            release.installer_url, installer_path, limit=expected_size, cancel_event=cancel_event
        )
        if cancel_event is not None and cancel_event.is_set():
            raise UpdateError("Download cancelled.")
        _download(release.checksum_url, checksum_path, limit=64 * 1024, cancel_event=cancel_event)
        checksum_text = checksum_path.read_text(encoding="utf-8")
        match = re.search(
            rf"(?im)^([0-9a-f]{{64}})\s+\*?{re.escape(release.installer_name)}\s*$",
            checksum_text,
        )
        if match is None or bytes.fromhex(match.group(1)) != digest:
            raise UpdateError("Installer SHA-256 verification failed.")
        if release.installer_size is not None and installer_path.stat().st_size != release.installer_size:
            raise UpdateError("Downloaded installer size does not match release metadata.")
        return installer_path
    except Exception:
        installer_path.unlink(missing_ok=True)
        raise
    finally:
        checksum_path.unlink(missing_ok=True)


def launch_installer(installer_path: Path) -> None:
    """Launch an already verified installer using the normal interactive wizard."""
    path = installer_path.resolve(strict=True)
    if platform_id() != "windows":
        raise UpdateError("Automatic installer launch is supported only on Windows; open the verified DMG manually.")
    if path.suffix.lower() != ".exe" or "NEXUS-updates" not in str(path):
        raise UpdateError("Refusing to launch an unexpected installer path.")
    if sys.platform != "win32":
        raise UpdateError("The Windows installer can only be launched on Windows.")
    try:
        subprocess.Popen([str(path)], close_fds=True)
    except OSError as exc:
        raise UpdateError(f"Could not start the verified installer: {exc}") from exc
