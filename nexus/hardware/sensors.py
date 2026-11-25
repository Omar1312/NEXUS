"""Optional CPU temperature access.

Windows does not expose CPU package temperature through a stable public API
(``psutil.sensors_temperatures`` is Linux-only). NEXUS therefore reports
"Unavailable" unless a supported hardware-monitoring bridge is running.

Supported bridge: LibreHardwareMonitor or OpenHardwareMonitor exposing its WMI
namespace. Both are optional third-party tools; NEXUS never installs or starts
them. Reading that namespace usually requires the monitoring tool to run as
administrator, which is outside NEXUS's control.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

log = logging.getLogger(__name__)

_LHM_NAMESPACES = (
    r"root\LibreHardwareMonitor",
    r"root\OpenHardwareMonitor",
)

DEFAULT_EXPLANATION = (
    "Windows 11 does not expose CPU temperature to user applications. "
    "NEXUS shows this sensor only when LibreHardwareMonitor or "
    "OpenHardwareMonitor is running and publishing its WMI sensors."
)


@dataclass(frozen=True, slots=True)
class TemperatureReading:
    celsius: float | None
    source: str
    explanation: str = ""


class CpuTemperatureSensor:
    """Lazily probes optional WMI sensor bridges once per process."""

    def __init__(self, *, enabled: bool = True) -> None:
        self._enabled = enabled
        self._probed = False
        self._namespace: str | None = None
        self._explanation = DEFAULT_EXPLANATION
        self._source = "Unavailable"
        self._last_error = ""

    @property
    def explanation(self) -> str:
        return self._explanation

    @property
    def source(self) -> str:
        return self._source

    @property
    def available(self) -> bool:
        self.read()
        return self._namespace is not None

    def _probe(self) -> None:
        if self._probed:
            return
        self._probed = True
        if not self._enabled:
            self._explanation = "CPU temperature probing is disabled in Settings."
            return
        try:
            import pythoncom
            import win32com.client
        except ImportError:
            self._explanation = "pywin32 is not installed; WMI sensor bridge unavailable."
            return

        pythoncom.CoInitialize()
        for namespace in _LHM_NAMESPACES:
            try:
                service = win32com.client.GetObject(f"winmgmts:\\\\.\\{namespace}")
                # A cheap query proves the namespace is live before we cache it.
                service.ExecQuery("SELECT Name FROM Sensor WHERE SensorType='Temperature'")
            except Exception as exc:  # com_error and friends
                self._last_error = str(exc)
                log.debug("Sensor namespace %s unavailable: %s", namespace, exc)
                continue
            self._namespace = namespace
            tool = "LibreHardwareMonitor" if "Libre" in namespace else "OpenHardwareMonitor"
            self._source = f"{tool} (WMI)"
            self._explanation = f"Provided by {tool} through its local WMI sensor namespace."
            log.info("CPU temperature source detected: %s", namespace)
            return
        log.info("No optional WMI temperature bridge detected.")

    def read(self) -> TemperatureReading:
        self._probe()
        if self._namespace is None:
            return TemperatureReading(None, "Unavailable", self._explanation)
        try:
            import pythoncom
            import win32com.client

            pythoncom.CoInitialize()
            service = win32com.client.GetObject(f"winmgmts:\\\\.\\{self._namespace}")
            rows = service.ExecQuery(
                "SELECT Name, Value FROM Sensor WHERE SensorType='Temperature'"
            )
            candidates: list[tuple[int, float]] = []
            for row in rows:
                name = str(getattr(row, "Name", "") or "")
                value = getattr(row, "Value", None)
                if value is None:
                    continue
                try:
                    celsius = float(value)
                except (TypeError, ValueError):
                    continue
                if not (-20.0 <= celsius <= 150.0):
                    continue
                lowered = name.lower()
                if "package" in lowered or "tctl" in lowered or "cpu" in lowered:
                    priority = 0 if "package" in lowered else 1
                    candidates.append((priority, celsius))
            if candidates:
                candidates.sort(key=lambda item: item[0])
                return TemperatureReading(round(candidates[0][1], 1), self._source, self._explanation)
            return TemperatureReading(None, self._source, "The sensor bridge exposes no CPU package temperature.")
        except Exception as exc:
            log.debug("Temperature read failed: %s", exc)
            self._namespace = None
            self._explanation = f"Sensor bridge stopped responding: {exc}"
            return TemperatureReading(None, "Unavailable", self._explanation)
