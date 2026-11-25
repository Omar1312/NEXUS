"""Process enumeration with safe, explicitly confirmed termination.

Safety model:

* Protected Windows processes are never offered for termination.
* NEXUS never terminates anything automatically or based on resource usage.
* Termination is graceful (``terminate()``); NEXUS does not call ``kill()``.
* A process that survives the grace period is reported honestly.
"""

from __future__ import annotations

import logging
import math
import os
import time
import sys
from dataclasses import dataclass

import psutil

log = logging.getLogger(__name__)

# Core components of Windows. Terminating any of these can bugcheck or log the
# user out, so they are hard-blocked in the UI and in the backend.
_PROTECTED_NAMES = {
    "system",
    "system idle process",
    "registry",
    "smss.exe",
    "csrss.exe",
    "wininit.exe",
    "winlogon.exe",
    "services.exe",
    "lsass.exe",
    "lsaiso.exe",
    "svchost.exe",
    "fontdrvhost.exe",
    "dwm.exe",
    "spoolsv.exe",
    "sihost.exe",
    "taskhostw.exe",
    "audiodg.exe",
    "wudfhost.exe",
    "msmpeng.exe",
    "nissrv.exe",
    "securityhealthservice.exe",
    "smartscreen.exe",
    "logonui.exe",
    "consent.exe",
    "memcompression",
    "ntoskrnl.exe",
}

# Shell/desktop processes that are not fatal but disruptive to stop.
_CAUTION_NAMES = {"explorer.exe"}
_MACOS_PROTECTED_NAMES = {
    "launchd", "kernel_task", "loginwindow", "windowserver", "launchservicesd",
    "runningboardd", "syslogd", "configd", "securityd", "notifyd",
    "opendirectoryd", "mds", "mdworker_shared", "trustd", "backupd",
}
_MACOS_CAUTION_NAMES = {"finder"}


@dataclass(frozen=True, slots=True)
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float
    memory_rss: int
    memory_percent: float
    status: str
    executable: str | None
    username: str | None
    create_time: float | None
    is_protected: bool = False
    protected_reason: str = ""

    @property
    def display_executable(self) -> str:
        return self.executable or "Access denied"


@dataclass(frozen=True, slots=True)
class TerminationAssessment:
    allowed: bool
    reason: str
    caution: str = ""


@dataclass(frozen=True, slots=True)
class TerminationResult:
    success: bool
    message: str
    still_running: bool = False


def assess_termination(info: ProcessInfo, *, current_pid: int | None = None) -> TerminationAssessment:
    """Decide whether the UI may offer termination for this process."""
    protected = "Protected system process" if sys.platform == "darwin" else "Protected Windows process"
    if info.is_protected:
        return TerminationAssessment(False, info.protected_reason or protected)
    if current_pid is not None and info.pid == current_pid:
        return TerminationAssessment(False, "NEXUS cannot terminate itself.")
    if info.pid <= 4:
        return TerminationAssessment(False, "Core kernel or system process (PID 4 or lower).")
    lowered = info.name.lower()
    protected_names = _MACOS_PROTECTED_NAMES if sys.platform == "darwin" else _PROTECTED_NAMES
    caution_names = _MACOS_CAUTION_NAMES if sys.platform == "darwin" else _CAUTION_NAMES
    if lowered in protected_names:
        return TerminationAssessment(False, "Core system process.")
    if lowered in caution_names:
        if sys.platform == "darwin":
            return TerminationAssessment(
                True, "Finder is the macOS desktop shell.",
                caution="Stopping Finder closes desktop windows and icons; macOS can relaunch it.",
            )
        return TerminationAssessment(
            True, "Windows Explorer is the desktop shell.",
            caution="Stopping Explorer closes the taskbar and desktop; Windows normally restarts it.",
        )
    if lowered == "nexus.exe":
        return TerminationAssessment(False, "This is the running NEXUS process.")
    return TerminationAssessment(True, "Eligible for graceful termination.")


def _protected_reason(name: str, pid: int) -> str:
    if pid <= 4:
        return "Core kernel or system process."
    protected_names = _MACOS_PROTECTED_NAMES if sys.platform == "darwin" else _PROTECTED_NAMES
    if name.lower() in protected_names:
        return "Blocked: critical system component."
    return ""


class ProcessSampler:
    """Caches :class:`psutil.Process` objects so CPU deltas are meaningful.

    Construct on the worker thread that samples it. The first sample reports
    zero CPU for all processes because Windows needs two observations to
    compute a delta.
    """

    def __init__(self) -> None:
        self._cache: dict[int, tuple[float, psutil.Process]] = {}
        self._details: dict[tuple[int, float], tuple[str | None, str | None]] = {}
        self._core_count = psutil.cpu_count(logical=True) or 1
        self._primed = False

    def _cached_details(self, pid: int, create_time: float, process: psutil.Process) -> tuple[str | None, str | None]:
        key = (pid, round(create_time, 2))
        if key in self._details:
            return self._details[key]
        executable = username = None
        try:
            executable = process.exe()
        except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
            pass
        try:
            username = process.username()
        except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
            pass
        if len(self._details) > 3000:
            self._details.clear()
        self._details[key] = (executable, username)
        return executable, username

    def sample(self) -> list[ProcessInfo]:
        results: list[ProcessInfo] = []
        seen: set[int] = set()
        for process in psutil.process_iter():
            pid = process.pid
            if pid == 0:
                continue
            try:
                create_time = process.create_time()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            seen.add(pid)
            cached = self._cache.get(pid)
            if cached is not None and abs(cached[0] - create_time) < 0.01:
                process = cached[1]
            else:
                try:
                    process.cpu_percent(None)
                    process.memory_info()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                self._cache[pid] = (create_time, process)

            try:
                name = process.name()
                status = process.status()
                memory = process.memory_info()
                cpu = process.cpu_percent(None) / self._core_count
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception as exc:  # pragma: no cover - defensive
                log.debug("Process %s could not be sampled: %s", pid, exc)
                continue

            executable, username = self._cached_details(pid, create_time, process)
            reason = _protected_reason(name, pid)
            if pid == os.getpid():
                reason = "This is the running NEXUS process."
            results.append(
                ProcessInfo(
                    pid=pid,
                    name=name,
                    cpu_percent=max(0.0, min(100.0, cpu)),
                    memory_rss=int(memory.rss),
                    memory_percent=round(100.0 * memory.rss / psutil.virtual_memory().total, 2),
                    status=_friendly_status(status),
                    executable=executable,
                    username=username,
                    create_time=create_time,
                    is_protected=bool(reason),
                    protected_reason=reason,
                )
            )

        # Drop dead PIDs so the cache cannot grow forever.
        for pid in list(self._cache):
            if pid not in seen:
                self._cache.pop(pid, None)
        self._primed = True
        results.sort(key=lambda p: p.cpu_percent, reverse=True)
        return results

    def readings_for(self, pid: int) -> tuple[float, int] | None:
        """Instantaneous (cpu_percent, rss) for a process details view."""
        try:
            process = psutil.Process(pid)
            cpu = process.cpu_percent(None) / self._core_count
            rss = process.memory_info().rss
            return cpu, int(rss)
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            return None


def _friendly_status(status: str) -> str:
    mapping = {
        "running": "Running",
        "sleeping": "Sleeping",
        "disk-sleep": "Waiting (disk)",
        "stopped": "Stopped",
        "zombie": "Zombie",
        "dead": "Dead",
        "wake-kill": "Wake/Kill",
        "waking": "Waking",
        "idle": "Idle",
        "locked": "Locked",
        "waiting": "Waiting",
        "suspended": "Suspended",
        "parked": "Parked",
    }
    return mapping.get(status, status.replace("-", " ").title())


@dataclass(frozen=True, slots=True)
class ProcessDetails:
    pid: int
    name: str
    executable: str | None
    command_line: str | None
    working_directory: str | None
    username: str | None
    status: str
    threads: int | None
    connections: int | None
    create_time: float | None
    cpu_percent: float | None
    memory_rss: int | None


def read_process_details(pid: int) -> ProcessDetails | None:
    try:
        process = psutil.Process(pid)
        with process.oneshot():
            memory = process.memory_info()
            try:
                connections = len(process.net_connections(kind="inet"))
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                connections = None
            return ProcessDetails(
                pid=pid,
                name=process.name(),
                executable=_safe(process.exe),
                command_line=_safe(lambda: " ".join(process.cmdline())),
                working_directory=_safe(process.cwd),
                username=_safe(process.username),
                status=_friendly_status(process.status()),
                threads=process.num_threads(),
                connections=connections,
                create_time=process.create_time(),
                cpu_percent=process.cpu_percent(None),
                memory_rss=int(memory.rss),
            )
    except (psutil.NoSuchProcess, psutil.AccessDenied, OSError) as exc:
        log.info("Process details unavailable for PID %s: %s", pid, exc)
        return None


def _safe(getter) -> str | None:
    try:
        value = getter()
        return str(value) if value else None
    except Exception:
        return None


def terminate_process(
    pid: int,
    *,
    expected_name: str,
    expected_create_time: float | None = None,
    timeout: float = 4.0,
) -> TerminationResult:
    """Gracefully terminate a process after re-validating its identity."""
    try:
        process = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return TerminationResult(False, "The process has already exited.")
    except psutil.AccessDenied:
        return TerminationResult(False, "Access denied. This process needs higher privileges.")

    try:
        actual_name = process.name()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return TerminationResult(False, "The process exited before it could be stopped.")
    if actual_name.lower() != expected_name.lower():
        return TerminationResult(
            False,
            f"PID {pid} now belongs to {actual_name!r}; the original process already exited.",
        )
    if expected_create_time is not None:
        if not math.isfinite(expected_create_time):
            return TerminationResult(False, "The original process identity could not be verified.")
        try:
            actual_create_time = process.create_time()
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            return TerminationResult(False, "The process exited before its identity could be verified.")
        if not math.isfinite(actual_create_time) or abs(actual_create_time - expected_create_time) >= 0.01:
            return TerminationResult(
                False,
                f"PID {pid} now belongs to a different process instance; nothing was terminated.",
            )

    assessment = assess_termination(
        ProcessInfo(
            pid=pid,
            name=actual_name,
            cpu_percent=0.0,
            memory_rss=0,
            memory_percent=0.0,
            status="",
            executable=None,
            username=None,
            create_time=None,
            is_protected=bool(_protected_reason(actual_name, pid)),
            protected_reason=_protected_reason(actual_name, pid),
        ),
        current_pid=os.getpid(),
    )
    if not assessment.allowed:
        return TerminationResult(False, assessment.reason)

    try:
        process.terminate()
    except psutil.AccessDenied:
        return TerminationResult(False, "Access denied. Try running NEXUS as administrator only if you trust the target.")
    except psutil.NoSuchProcess:
        return TerminationResult(True, "The process had already exited.")
    except OSError as exc:
        return TerminationResult(False, f"Termination request failed: {exc}")

    try:
        process.wait(timeout=timeout)
        return TerminationResult(True, f"{actual_name} (PID {pid}) closed.")
    except psutil.TimeoutExpired:
        return TerminationResult(
            False,
            f"{actual_name} did not exit within {timeout:.0f}s. Close it from its own window. "
            "NEXUS does not force-kill processes.",
            still_running=True,
        )
    except psutil.NoSuchProcess:
        return TerminationResult(True, f"{actual_name} (PID {pid}) closed.")


def top_processes(processes: list[ProcessInfo], *, key: str, limit: int = 5) -> list[ProcessInfo]:
    """Return the heaviest processes by ``cpu_percent`` or ``memory_rss``."""
    if key == "memory":
        ordered = sorted(processes, key=lambda p: p.memory_rss, reverse=True)
    else:
        ordered = sorted(processes, key=lambda p: p.cpu_percent, reverse=True)
    return ordered[:limit]


def elapsed_since(timestamp: float | None) -> float | None:
    return time.time() - timestamp if timestamp else None
