"""Tests for process sampling and safe termination rules."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock, patch

import psutil

from nexus.core.process_manager import (
    ProcessInfo,
    ProcessSampler,
    assess_termination,
    terminate_process,
)


def _info(pid: int, name: str, *, protected: bool = False) -> ProcessInfo:
    return ProcessInfo(
        pid=pid,
        name=name,
        cpu_percent=0.0,
        memory_rss=0,
        memory_percent=0.0,
        status="Running",
        executable=None,
        username=None,
        create_time=100.0,
        is_protected=protected,
    )


def test_process_sampler_normalizes_cpu_and_reports_memory():
    process = Mock()
    process.pid = 1234
    process.create_time.return_value = 100.0
    process.cpu_percent.side_effect = [0.0, 50.0]
    process.memory_info.return_value = SimpleNamespace(rss=250)
    process.name.return_value = "worker.exe"
    process.status.return_value = "running"
    process.exe.return_value = r"C:\Apps\worker.exe"
    process.username.return_value = "tester"

    with (
        patch("nexus.core.process_manager.psutil.cpu_count", return_value=4),
        patch("nexus.core.process_manager.psutil.virtual_memory", return_value=SimpleNamespace(total=1000)),
        patch("nexus.core.process_manager.psutil.process_iter", return_value=[process]),
    ):
        sample = ProcessSampler().sample()

    assert len(sample) == 1
    assert sample[0].cpu_percent == 12.5
    assert sample[0].memory_rss == 250
    assert sample[0].memory_percent == 25.0
    assert sample[0].status == "Running"


def test_process_sampler_skips_processes_that_disappear_or_are_denied():
    vanished = Mock()
    vanished.pid = 123
    vanished.create_time.side_effect = psutil.NoSuchProcess(123)

    denied = Mock()
    denied.pid = 456
    denied.create_time.return_value = 100.0
    denied.cpu_percent.side_effect = psutil.AccessDenied(456)

    with (
        patch("nexus.core.process_manager.psutil.cpu_count", return_value=4),
        patch("nexus.core.process_manager.psutil.process_iter", return_value=[vanished, denied]),
    ):
        sample = ProcessSampler().sample()

    assert sample == []


def test_termination_assessment_blocks_self_and_protected_processes():
    assert not assess_termination(_info(4, "System")).allowed
    assert not assess_termination(_info(1234, "worker.exe", protected=True)).allowed
    assert not assess_termination(_info(1234, "worker.exe"), current_pid=1234).allowed
    explorer = assess_termination(_info(2222, "explorer.exe"))
    assert explorer.allowed
    assert explorer.caution


def test_termination_rejects_reused_pid_even_when_name_matches():
    process = Mock()
    process.name.return_value = "worker.exe"
    process.create_time.return_value = 200.0

    with (
        patch("nexus.core.process_manager.psutil.Process", return_value=process),
        patch("nexus.core.process_manager.os.getpid", return_value=9999),
    ):
        result = terminate_process(
            1234, expected_name="worker.exe", expected_create_time=100.0
        )

    assert not result.success
    assert "different process instance" in result.message
    process.terminate.assert_not_called()


def test_termination_rejects_name_change_and_access_denied():
    renamed = Mock()
    renamed.name.return_value = "different.exe"
    denied = Mock()
    denied.name.side_effect = psutil.AccessDenied(1235)

    with (
        patch(
            "nexus.core.process_manager.psutil.Process",
            side_effect=[renamed, denied],
        ),
        patch("nexus.core.process_manager.os.getpid", return_value=9999),
    ):
        name_result = terminate_process(1234, expected_name="worker.exe")
        denied_result = terminate_process(1235, expected_name="worker.exe")

    assert not name_result.success
    assert "now belongs" in name_result.message
    assert not denied_result.success
    renamed.terminate.assert_not_called()
    denied.terminate.assert_not_called()


def test_termination_is_graceful_and_reports_timeout_without_force_kill():
    process = Mock()
    process.name.return_value = "worker.exe"
    process.create_time.return_value = 100.0
    process.wait.side_effect = psutil.TimeoutExpired(4)

    with (
        patch("nexus.core.process_manager.psutil.Process", return_value=process),
        patch("nexus.core.process_manager.os.getpid", return_value=9999),
    ):
        result = terminate_process(
            1234, expected_name="worker.exe", expected_create_time=100.0, timeout=4.0
        )

    assert not result.success
    assert result.still_running
    process.terminate.assert_called_once_with()
    process.kill.assert_not_called()
