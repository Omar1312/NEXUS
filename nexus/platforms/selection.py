"""Platform identification without importing OS-specific APIs."""

from __future__ import annotations

import platform
import sys

from nexus.utils.exceptions import UnsupportedPlatformError

SUPPORTED_PLATFORMS = frozenset({"windows", "macos"})


def platform_id(system: str | None = None) -> str:
    """Return the NEXUS platform key for a Python platform identifier."""
    value = sys.platform if system is None else system
    if value == "win32":
        return "windows"
    if value == "darwin":
        return "macos"
    raise UnsupportedPlatformError(
        f"NEXUS currently supports Windows and macOS; detected platform {value!r}."
    )


def architecture_id(machine: str | None = None) -> str:
    """Normalize a common CPU architecture name without asserting compatibility."""
    value = (platform.machine() if machine is None else machine).casefold()
    if value in {"arm64", "aarch64"}:
        return "arm64"
    if value in {"amd64", "x86_64", "x64"}:
        return "x64"
    return value or "unknown"
