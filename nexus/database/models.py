"""Typed records returned by the history repository."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MetricRow:
    ts: float
    cpu_percent: float | None = None
    cpu_temp_c: float | None = None
    memory_percent: float | None = None
    memory_used_bytes: int | None = None
    disk_read_bps: float | None = None
    disk_write_bps: float | None = None
    disk_activity_percent: float | None = None
    net_down_bps: float | None = None
    net_up_bps: float | None = None
    gpu_percent: float | None = None
    gpu_mem_percent: float | None = None
    gpu_temp_c: float | None = None
    score: float | None = None

    @classmethod
    def from_row(cls, row) -> MetricRow:  # sqlite3.Row
        keys = set(row.keys())
        return cls(**{name: row[name] for name in cls.__dataclass_fields__ if name in keys})


@dataclass(frozen=True, slots=True)
class GamingSessionRow:
    id: int
    started_at: float
    ended_at: float | None
    summary_json: str | None
    samples_json: str | None
