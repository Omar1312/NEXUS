"""NVIDIA GPU metrics through NVML (nvidia-ml-py).

Each field is read independently: laptop GPUs and older drivers expose
different subsets, and an unsupported field must never invalidate the whole
sample. Non-NVIDIA adapters are reported as names only, with metrics
"Unavailable".
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from nexus.core.metrics import Capability, GpuMetrics
from nexus.hardware.windows import display_adapter_names

log = logging.getLogger(__name__)

MIB = 1024 * 1024


class GpuCollector:
    def __init__(self) -> None:
        self._pynvml: Any | None = None
        self._handles: list[Any] = []
        self._names: list[str] = []
        self._driver: str | None = None
        self._init_error: str | None = None
        self._warned: set[str] = set()
        self._init()

    # -- lifecycle ----------------------------------------------------------
    def _init(self) -> None:
        try:
            import pynvml

            pynvml.nvmlInit()
            self._pynvml = pynvml
            count = pynvml.nvmlDeviceGetCount()
            for index in range(count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(index)
                raw_name = pynvml.nvmlDeviceGetName(handle)
                name = raw_name.decode("utf-8", "replace") if isinstance(raw_name, bytes) else str(raw_name)
                self._handles.append(handle)
                self._names.append(name)
            try:
                raw_driver = pynvml.nvmlSystemGetDriverVersion()
                self._driver = (
                    raw_driver.decode("utf-8", "replace")
                    if isinstance(raw_driver, bytes)
                    else str(raw_driver)
                )
            except Exception:
                self._driver = None
            log.info("NVML initialised: %d GPU(s), driver %s", len(self._handles), self._driver)
        except Exception as exc:
            self._init_error = str(exc)
            log.info("NVML unavailable (%s); NVIDIA metrics will be reported as unavailable.", exc)

    @property
    def available(self) -> bool:
        return bool(self._handles)

    @property
    def driver_version(self) -> str | None:
        return self._driver

    @property
    def init_error(self) -> str | None:
        return self._init_error

    @property
    def names(self) -> list[str]:
        if self._names:
            return list(self._names)
        return display_adapter_names()

    def _safe(self, label: str, getter: Callable[[], Any]) -> Any | None:
        if self._pynvml is None:
            return None
        try:
            return getter()
        except Exception as exc:
            if label not in self._warned:
                self._warned.add(label)
                log.info("GPU metric %s unsupported: %s", label, exc)
            return None

    def sample(self) -> tuple[GpuMetrics, ...]:
        if not self._handles or self._pynvml is None:
            return ()
        results: list[GpuMetrics] = []
        nvml = self._pynvml
        for index, handle in enumerate(self._handles):
            utilization = self._safe(
                "utilization", lambda h=handle: nvml.nvmlDeviceGetUtilizationRates(h)
            )
            memory = self._safe("memory", lambda h=handle: nvml.nvmlDeviceGetMemoryInfo(h))
            temperature = self._safe(
                "temperature",
                lambda h=handle: nvml.nvmlDeviceGetTemperature(h, nvml.NVML_TEMPERATURE_GPU),
            )
            power_mw = self._safe("power", lambda h=handle: nvml.nvmlDeviceGetPowerUsage(h))
            power_limit_mw = self._safe(
                "power_limit",
                lambda h=handle: nvml.nvmlDeviceGetPowerManagementLimit(h),
            )
            fan = self._safe("fan", lambda h=handle: nvml.nvmlDeviceGetFanSpeed(h))
            clock = self._safe(
                "clock",
                lambda h=handle: nvml.nvmlDeviceGetClockInfo(h, nvml.NVML_CLOCK_GRAPHICS),
            )
            results.append(
                GpuMetrics(
                    name=self._names[index] if index < len(self._names) else f"GPU {index}",
                    index=index,
                    utilization_percent=(
                        float(utilization.gpu) if utilization is not None else None
                    ),
                    memory_used_bytes=int(memory.used) if memory is not None else None,
                    memory_total_bytes=int(memory.total) if memory is not None else None,
                    memory_utilization_percent=(
                        float(utilization.memory) if utilization is not None else None
                    ),
                    temperature_c=float(temperature) if temperature is not None else None,
                    power_watts=round(float(power_mw) / 1000.0, 1) if power_mw is not None else None,
                    power_limit_watts=(
                        round(float(power_limit_mw) / 1000.0, 1)
                        if power_limit_mw is not None
                        else None
                    ),
                    fan_percent=float(fan) if fan is not None else None,
                    core_clock_mhz=float(clock) if clock is not None else None,
                    driver_version=self._driver,
                )
            )
        return tuple(results)

    def capabilities(self) -> list[Capability]:
        if not self._handles:
            adapters = display_adapter_names()
            detail = (
                f"NVML initialisation failed: {self._init_error}"
                if self._init_error
                else "No NVIDIA GPU with an NVML driver was detected."
            )
            return [
                Capability("gpu.core", "GPU utilization", False, detail),
                Capability("gpu.memory", "GPU memory", False, detail),
                Capability("gpu.temperature", "GPU temperature", False, detail),
                Capability("gpu.power", "GPU power", False, detail),
                Capability("gpu.fan", "GPU fan", False, detail),
            ] + (
                [Capability("gpu.name", f"Adapter: {', '.join(adapters)}", True, "Name only; metrics unavailable.")]
                if adapters
                else []
            )
        return [
            Capability("gpu.core", "GPU utilization", True, "NVIDIA NVML"),
            Capability("gpu.memory", "GPU memory", True, "NVIDIA NVML"),
            Capability("gpu.temperature", "GPU temperature", True, "NVIDIA NVML"),
            Capability("gpu.power", "GPU power", True, "NVIDIA NVML"),
            Capability(
                "gpu.fan",
                "GPU fan",
                self._safe("fan", lambda: nvml_fan(self._pynvml, self._handles[0])) is not None,
                "Some laptop GPUs do not expose a fan tachometer.",
            ),
        ]

    def close(self) -> None:
        if self._pynvml is not None:
            try:
                self._pynvml.nvmlShutdown()
            except Exception:
                pass
            self._pynvml = None
            self._handles.clear()
            log.debug("NVML shut down.")


def nvml_fan(pynvml: Any, handle: Any) -> int | None:
    try:
        return int(pynvml.nvmlDeviceGetFanSpeed(handle))
    except Exception:
        return None
