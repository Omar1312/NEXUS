from __future__ import annotations

import sys
import types

from nexus.core.collectors import SystemCollector
from nexus.hardware.gpu import GpuCollector
from nexus.hardware.sensors import CpuTemperatureSensor


def test_missing_nvml_keeps_other_system_metrics_available(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "pynvml", None)
    collector = SystemCollector(enable_wmi_sensors=False)
    try:
        snapshot = collector.collect()
        assert snapshot.cpu is not None
        assert snapshot.memory is not None
        assert snapshot.disk is not None
        assert snapshot.network is not None
        assert snapshot.gpus == ()
        assert any("GPU metrics unavailable" in warning for warning in snapshot.warnings)
        assert not collector.gpu.available
        capabilities = collector.gpu.capabilities()
        assert not any(item.available for item in capabilities if item.key.startswith("gpu.") and item.key != "gpu.name")
        assert all("Name only" in item.detail for item in capabilities if item.key == "gpu.name")
    finally:
        collector.close()


def test_missing_wmi_dependencies_report_unavailable(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "pythoncom", None)
    sensor = CpuTemperatureSensor()
    reading = sensor.read()
    assert reading.celsius is None
    assert reading.source == "Unavailable"
    assert "pywin32 is not installed" in reading.explanation


def test_nvml_initialization_failure_is_isolated(monkeypatch) -> None:
    fake = types.SimpleNamespace(nvmlInit=lambda: (_ for _ in ()).throw(RuntimeError("no driver")))
    monkeypatch.setitem(sys.modules, "pynvml", fake)
    gpu = GpuCollector()
    assert not gpu.available
    assert "no driver" in gpu.init_error
    assert gpu.sample() == ()

