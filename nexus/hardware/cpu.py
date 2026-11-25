"""CPU metrics via psutil plus optional temperature bridge."""

from __future__ import annotations

import logging

import psutil

from nexus.core.metrics import Capability, CpuMetrics
from nexus.hardware.pdh import _PdhQuery
from nexus.hardware.sensors import CpuTemperatureSensor
from nexus.hardware.windows import cpu_brand

log = logging.getLogger(__name__)


class CpuCollector:
    def __init__(self, temperature_sensor: CpuTemperatureSensor | None = None) -> None:
        self._model = cpu_brand()
        self._physical = psutil.cpu_count(logical=False)
        self._logical = psutil.cpu_count(logical=True)
        self._temperature = temperature_sensor or CpuTemperatureSensor()
        self._pdh = _PdhQuery()
        self._nominal_mhz = self._base_frequency()
        # Prime psutil's non-blocking sampler so the first real sample is meaningful.
        try:
            psutil.cpu_percent(interval=None)
            psutil.cpu_percent(interval=None, percpu=True)
        except Exception as exc:  # pragma: no cover - defensive
            log.debug("CPU sampler priming failed: %s", exc)

    @staticmethod
    def _base_frequency() -> float | None:
        """Nominal clock, used as the base for the PDH performance percentage."""
        try:
            frequency = psutil.cpu_freq()
        except Exception:
            return None
        if frequency is None:
            return None
        for candidate in (frequency.max, frequency.current):
            value = float(candidate or 0.0)
            if value > 0:
                return value
        return None

    @property
    def model(self) -> str:
        return self._model

    @property
    def physical_cores(self) -> int | None:
        return self._physical

    @property
    def logical_cores(self) -> int | None:
        return self._logical

    def _frequency_mhz(self) -> float | None:
        # PDH reports the processor's current performance relative to nominal.
        # Multiplying by the base clock gives the real current frequency, which
        # is far more useful than psutil's static Windows value.
        if self._nominal_mhz:
            percent = self._pdh.read_percent()
            if percent is not None:
                current = self._nominal_mhz * percent / 100.0
                if 100.0 <= current <= 20_000.0:
                    return round(current, 0)
        try:
            frequency = psutil.cpu_freq()
        except Exception:
            return None
        if frequency is None:
            return None
        current = float(frequency.current)
        # Windows frequently reports 0 when the value is unknown.
        return current if current > 0 else None

    def close(self) -> None:
        self._pdh.close()

    def sample(self) -> CpuMetrics:
        try:
            total = psutil.cpu_percent(interval=None)
            per_core = tuple(psutil.cpu_percent(interval=None, percpu=True))
        except Exception as exc:
            log.warning("CPU utilization sample failed: %s", exc)
            total, per_core = None, ()
        temperature = self._temperature.read().celsius
        return CpuMetrics(
            model=self._model,
            utilization_percent=float(total) if total is not None else None,
            per_core_percent=per_core,
            physical_cores=self._physical,
            logical_cores=self._logical,
            frequency_mhz=self._frequency_mhz(),
            temperature_c=temperature,
        )

    def capabilities(self) -> list[Capability]:
        temp = self._temperature.read()
        return [
            Capability("cpu.usage", "CPU utilization", True, "Sampled from Windows performance counters."),
            Capability(
                "cpu.frequency",
                "CPU frequency",
                self._frequency_mhz() is not None,
                "" if self._frequency_mhz() is not None else "The platform does not report current clock speed.",
            ),
            Capability(
                "cpu.temperature",
                "CPU temperature",
                temp.celsius is not None,
                temp.explanation if temp.celsius is None else temp.source,
            ),
        ]

    @property
    def temperature_explanation(self) -> str:
        return self._temperature.explanation
