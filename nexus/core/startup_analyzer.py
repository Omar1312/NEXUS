"""Windows startup-entry discovery (read-only).

Supported sources:

* ``HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run``
* ``HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run`` (64- and 32-bit views)
* User and all-users Startup folders (``.lnk`` shortcuts resolved via WScript.Shell)

NEXUS never writes, deletes or disables startup entries. It deliberately does
not estimate per-entry boot impact: Windows does not expose that number through
a supported API, and measuring it would require boot tracing. Entries are shown
as "Not measured".
"""

from __future__ import annotations

import logging
import os
import shutil
import time
from dataclasses import dataclass, replace
from pathlib import Path

from nexus.utils.exceptions import UnsupportedPlatformError

log = logging.getLogger(__name__)

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
IMPACT_NOTE = "Not measured"

_SYSTEMROOT = os.environ.get("SystemRoot", r"C:\Windows")


@dataclass(frozen=True, slots=True)
class StartupEntry:
    name: str
    command: str
    executable: str | None
    arguments: str
    source: str
    location: str
    scope: str
    publisher: str | None = None
    file_version: str | None = None
    file_exists: bool = False
    file_size_bytes: int | None = None
    kind: str = "registry"
    impact: str = IMPACT_NOTE

    @property
    def status(self) -> str:
        if self.executable and not self.file_exists:
            return "Target missing"
        if not self.executable:
            return "Unresolved"
        return "Registered"


@dataclass(frozen=True, slots=True)
class StartupScanResult:
    entries: tuple[StartupEntry, ...]
    errors: tuple[str, ...]
    scanned_at: float
    duration_ms: float


def _version_info(path: str) -> tuple[str | None, str | None]:
    try:
        import win32api

        info = win32api.GetFileVersionInfo(path, "\\")
        tables = info.get("StringFileInfo", {})
        for table in tables.values():
            company = table.get("CompanyName")
            version = table.get("FileVersion") or table.get("ProductVersion")
            if company or version:
                return (str(company).strip() if company else None, str(version) if version else None)
    except Exception as exc:
        log.debug("Version info unavailable for %s: %s", path, exc)
    return None, None


def _looks_like_path(text: str) -> bool:
    return os.path.isabs(text) or text.startswith("%")


def resolve_executable(command: str) -> tuple[str | None, str]:
    """Split a startup command line into ``(executable, arguments)``.

    Handles quoted paths, unquoted paths containing spaces, environment
    variables and bare executables resolved from PATH/System32.
    """
    command = command.strip()
    if not command:
        return None, ""
    executable = ""
    arguments = ""
    if command.startswith('"'):
        closing = command.find('"', 1)
        if closing == -1:
            executable, arguments = command[1:], ""
        else:
            executable = command[1:closing]
            arguments = command[closing + 1 :].strip()
    else:
        first, _, rest = command.partition(" ")
        if _looks_like_path(first) and Path(os.path.expandvars(first)).exists():
            executable, arguments = first, rest
        else:
            # An unquoted path may contain spaces: pick the longest existing prefix.
            resolved = None
            candidate = command
            while " " in candidate:
                candidate = candidate.rsplit(" ", 1)[0]
                expanded = os.path.expandvars(candidate)
                if os.path.exists(expanded):
                    resolved = expanded
                    arguments = command[len(candidate) :].strip()
                    break
            if resolved:
                executable, arguments = resolved, arguments
            else:
                executable, arguments = first, rest

    expanded = os.path.expandvars(executable)
    if not os.path.isabs(expanded):
        found = shutil.which(expanded)
        if not found:
            candidate = Path(_SYSTEMROOT) / "System32" / expanded
            found = str(candidate) if candidate.exists() else None
        expanded = found or expanded
    return (expanded or None), arguments


def _entry_from_values(
    name: str,
    command: str,
    source: str,
    location: str,
    scope: str,
    kind: str,
) -> StartupEntry:
    executable, arguments = resolve_executable(command)
    publisher = version = None
    size = None
    exists = bool(executable and Path(executable).exists())
    if exists and executable:
        publisher, version = _version_info(executable)
        try:
            size = Path(executable).stat().st_size
        except OSError:
            size = None
    return StartupEntry(
        name=name,
        command=command,
        executable=executable,
        arguments=arguments,
        source=source,
        location=location,
        scope=scope,
        publisher=publisher,
        file_version=version,
        file_exists=exists,
        file_size_bytes=size,
        kind=kind,
    )


class StartupAnalyzer:
    def scan(self) -> StartupScanResult:
        started = time.perf_counter()
        errors: list[str] = []
        entries: dict[tuple[str, str], StartupEntry] = {}

        if os.name != "nt":
            raise UnsupportedPlatformError("Startup analysis requires Windows.")
        import winreg

        views = (
            ("Registry (current user)", winreg.HKEY_CURRENT_USER, RUN_KEY, "User", 0),
            (
                "Registry (all users, 64-bit)",
                winreg.HKEY_LOCAL_MACHINE,
                RUN_KEY,
                "Machine",
                winreg.KEY_WOW64_64KEY,
            ),
            (
                "Registry (all users, 32-bit)",
                winreg.HKEY_LOCAL_MACHINE,
                RUN_KEY,
                "Machine",
                winreg.KEY_WOW64_32KEY,
            ),
        )
        seen_registry: set[str] = set()
        for source, hive, path, scope, view in views:
            try:
                with winreg.OpenKey(hive, path, 0, winreg.KEY_READ | view) as key:
                    index = 0
                    while True:
                        try:
                            value_name, value_data, _kind = winreg.EnumValue(key, index)
                        except OSError:
                            break
                        index += 1
                        if not isinstance(value_data, str) or not value_data.strip():
                            continue
                        dedup_key = value_name.lower()
                        if dedup_key in seen_registry:
                            continue
                        seen_registry.add(dedup_key)
                        entry = _entry_from_values(
                            name=value_name,
                            command=value_data,
                            source=source,
                            location=f"{'HKCU' if hive == winreg.HKEY_CURRENT_USER else 'HKLM'}\\{path}",
                            scope=scope,
                            kind="registry",
                        )
                        entries[(source, value_name)] = entry
            except FileNotFoundError:
                continue
            except OSError as exc:
                errors.append(f"{source}: {exc}")

        folders = (
            (
                "Startup folder (current user)",
                Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs\Startup",
                "User",
            ),
            (
                "Startup folder (all users)",
                Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData"))
                / r"Microsoft\Windows\Start Menu\Programs\Startup",
                "Machine",
            ),
        )
        for source, folder, scope in folders:
            if not folder.is_dir():
                continue
            try:
                children = sorted(folder.iterdir(), key=lambda p: p.name.lower())
            except OSError as exc:
                errors.append(f"{source}: {exc}")
                continue
            for child in children:
                if child.name.lower() == "desktop.ini":
                    continue
                if child.suffix.lower() == ".lnk":
                    command, target = self._read_shortcut(child)
                    if not command:
                        errors.append(f"{source}: could not resolve shortcut {child.name}")
                        continue
                    entry = _entry_from_values(
                        name=child.stem,
                        command=command,
                        source=source,
                        location=str(folder),
                        scope=scope,
                        kind="shortcut",
                    )
                    # Prefer the shortcut's own metadata path for existence checks.
                    if target and not entry.file_exists:
                        publisher, version = _version_info(target)
                        entry = replace(
                            entry,
                            executable=target,
                            publisher=publisher,
                            file_version=version,
                            file_exists=Path(target).exists(),
                        )
                    entries[(source, child.name)] = entry
                elif child.is_file() and child.suffix.lower() in (".exe", ".bat", ".cmd", ".vbs", ".ps1"):
                    entries[(source, child.name)] = _entry_from_values(
                        name=child.stem,
                        command=f'"{child}"',
                        source=source,
                        location=str(folder),
                        scope=scope,
                        kind="folder",
                    )

        ordered = sorted(entries.values(), key=lambda e: (e.scope, e.source, e.name.lower()))
        return StartupScanResult(
            entries=tuple(ordered),
            errors=tuple(errors),
            scanned_at=time.time(),
            duration_ms=round((time.perf_counter() - started) * 1000.0, 1),
        )

    @staticmethod
    def _read_shortcut(path: Path) -> tuple[str | None, str | None]:
        try:
            import pythoncom
            import win32com.client

            pythoncom.CoInitialize()
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortcut(str(path))
            target = str(shortcut.TargetPath or "")
            arguments = str(shortcut.Arguments or "")
            if not target:
                return None, None
            command = f'"{target}"' + (f" {arguments}" if arguments else "")
            return command, target
        except Exception as exc:
            log.debug("Shortcut resolution failed for %s: %s", path, exc)
            return None, None
