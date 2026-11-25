"""Shell integration helpers used by several pages."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

log = logging.getLogger(__name__)


def open_uri(uri: str) -> bool:
    """Open a URI or path with the user's default handler."""
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", uri], close_fds=True)
        elif sys.platform == "win32":
            os.startfile(uri)  # type: ignore[attr-defined]
        else:
            return False
        return True
    except (OSError, AttributeError) as exc:
        log.warning("Could not open %s: %s", uri, exc)
        return False


def reveal_in_explorer(path: str) -> bool:
    """Reveal a file or open its containing folder using the native file manager."""
    candidate = Path(path)
    if sys.platform == "darwin":
        target = candidate if candidate.exists() else candidate.parent
        try:
            subprocess.Popen(["open", "-R", str(target)], close_fds=True)
            return True
        except OSError as exc:
            log.warning("Finder reveal failed: %s", exc)
            return False
    if candidate.exists():
        try:
            subprocess.Popen(["explorer.exe", f"/select,{candidate}"])
            return True
        except OSError as exc:
            log.warning("Explorer select failed: %s", exc)
    folder = candidate.parent if candidate.parent.exists() else candidate
    return open_uri(str(folder))
