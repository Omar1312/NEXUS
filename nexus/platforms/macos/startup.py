"""Read-only discovery of the current user's macOS LaunchAgents."""

from __future__ import annotations

import os
import plistlib
import shlex
import time
from pathlib import Path

from nexus.core.startup_analyzer import StartupEntry, StartupScanResult


class MacStartupAnalyzer:
    """Inspect user LaunchAgents without changing login configuration."""

    def scan(self) -> StartupScanResult:
        started = time.perf_counter()
        folder = Path.home() / "Library" / "LaunchAgents"
        entries: list[StartupEntry] = []
        errors: list[str] = []
        try:
            children = sorted(folder.glob("*.plist"), key=lambda item: item.name.lower()) if folder.is_dir() else []
        except OSError as exc:
            children = []
            errors.append(f"User LaunchAgents: {exc}")
        for path in children[:2000]:
            try:
                with path.open("rb") as stream:
                    payload = plistlib.load(stream)
                if not isinstance(payload, dict):
                    raise ValueError("property list root is not a dictionary")
                program_args = payload.get("ProgramArguments")
                if isinstance(program_args, list) and program_args:
                    args = [str(value) for value in program_args]
                    executable = args[0]
                    command = shlex.join(args)
                    arguments = shlex.join(args[1:])
                else:
                    executable = str(payload.get("Program") or "")
                    command = shlex.quote(executable) if executable else ""
                    arguments = ""
                exists = bool(executable and Path(executable).exists())
                size = Path(executable).stat().st_size if exists and Path(executable).is_file() else None
                label = str(payload.get("Label") or path.stem)
                entries.append(StartupEntry(
                    name=label,
                    command=command or "(no Program or ProgramArguments)",
                    executable=executable or None,
                    arguments=arguments,
                    source="User LaunchAgent",
                    location=str(path),
                    scope="User",
                    file_exists=exists,
                    file_size_bytes=size,
                    kind="launchagent",
                    impact="Not measured",
                ))
            except (OSError, plistlib.InvalidFileException, ValueError, TypeError) as exc:
                errors.append(f"{path.name}: {exc}")
        if len(children) > 2000:
            errors.append("User LaunchAgents: scan limited to the first 2,000 files")
        return StartupScanResult(
            entries=tuple(sorted(entries, key=lambda item: item.name.lower())),
            errors=tuple(errors), scanned_at=time.time(),
            duration_ms=round((time.perf_counter() - started) * 1000.0, 1),
        )


def startup_analyzer():
    if os.sys.platform == "darwin":
        return MacStartupAnalyzer()
    from nexus.core.startup_analyzer import StartupAnalyzer
    return StartupAnalyzer()
