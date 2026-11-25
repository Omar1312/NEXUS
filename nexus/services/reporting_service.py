"""Report generation in CSV, JSON and HTML formats.

Reports are built from measured data only. Unavailable metrics are listed as
"Unavailable" rather than zero-filled, and hostnames are omitted unless the
user explicitly opts in.
"""

from __future__ import annotations

import csv
import html
import io
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Iterable, Sequence

from nexus import __version__
from nexus.core.metrics import Snapshot
from nexus.core.recommendations import Recommendation
from nexus.core.scoring import METHODOLOGY, ScoreReport
from nexus.database.models import MetricRow
from nexus.utils import formatting

UNITS = {
    "cpu_percent": "%",
    "cpu_temp_c": "°C",
    "memory_percent": "%",
    "memory_used_bytes": "bytes",
    "disk_read_bps": "bytes/s",
    "disk_write_bps": "bytes/s",
    "disk_activity_percent": "%",
    "net_down_bps": "bytes/s",
    "net_up_bps": "bytes/s",
    "gpu_percent": "%",
    "gpu_mem_percent": "%",
    "gpu_temp_c": "°C",
}

LABELS = {
    "cpu_percent": "CPU utilization",
    "cpu_temp_c": "CPU temperature",
    "memory_percent": "Memory utilization",
    "memory_used_bytes": "Memory used",
    "disk_read_bps": "Disk read",
    "disk_write_bps": "Disk write",
    "disk_activity_percent": "Disk activity",
    "net_down_bps": "Network download",
    "net_up_bps": "Network upload",
    "gpu_percent": "GPU utilization",
    "gpu_mem_percent": "GPU memory utilization",
    "gpu_temp_c": "GPU temperature",
}


@dataclass(frozen=True, slots=True)
class MetricStatistic:
    key: str
    label: str
    unit: str
    minimum: float | None
    maximum: float | None
    average: float | None
    samples: int


@dataclass(frozen=True, slots=True)
class ReportData:
    generated_at: float
    period_start: float | None
    period_end: float | None
    system: dict[str, object]
    metrics: tuple[MetricStatistic, ...]
    score: dict[str, object]
    recommendations: tuple[dict[str, object], ...]
    missing: tuple[str, ...]
    notes: tuple[str, ...]
    app_version: str = __version__
    include_hostname: bool = False

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["generated_at_iso"] = datetime.fromtimestamp(self.generated_at).isoformat(
            timespec="seconds"
        )
        if self.period_start is not None:
            payload["period_start_iso"] = datetime.fromtimestamp(self.period_start).isoformat(
                timespec="seconds"
            )
        if self.period_end is not None:
            payload["period_end_iso"] = datetime.fromtimestamp(self.period_end).isoformat(
                timespec="seconds"
            )
        return payload


def summarize_rows(rows: Sequence[MetricRow]) -> tuple[MetricStatistic, ...]:
    stats: list[MetricStatistic] = []
    for key, label in LABELS.items():
        values = [getattr(row, key) for row in rows if getattr(row, key) is not None]
        if not values:
            stats.append(MetricStatistic(key, label, UNITS[key], None, None, None, 0))
            continue
        numeric = [float(v) for v in values]
        stats.append(
            MetricStatistic(
                key=key,
                label=label,
                unit=UNITS[key],
                minimum=round(min(numeric), 2),
                maximum=round(max(numeric), 2),
                average=round(sum(numeric) / len(numeric), 2),
                samples=len(numeric),
            )
        )
    return tuple(stats)


def build_report(
    *,
    snapshot: Snapshot | None,
    rows: Sequence[MetricRow],
    score: ScoreReport | None,
    recommendations: Iterable[Recommendation],
    missing_metrics: Iterable[str],
    include_hostname: bool = False,
    notes: Iterable[str] = (),
) -> ReportData:
    system: dict[str, object] = {}
    if snapshot is not None:
        info = snapshot.system
        if info is not None:
            system = {
                "operating_system": info.os_name,
                "os_version": info.os_version,
                "architecture": info.architecture,
                "hostname": info.hostname if include_hostname else "Omitted",
            }
        if snapshot.cpu is not None:
            system["cpu"] = snapshot.cpu.model
            system["physical_cores"] = snapshot.cpu.physical_cores
            system["logical_cores"] = snapshot.cpu.logical_cores
        if snapshot.memory is not None:
            system["memory_total_bytes"] = snapshot.memory.total_bytes
        if snapshot.gpus:
            system["gpu"] = snapshot.gpus[0].name
            system["gpu_driver"] = snapshot.gpus[0].driver_version or "Unknown"
        if snapshot.disk is not None:
            system["volumes"] = [
                {
                    "mountpoint": p.mountpoint,
                    "filesystem": p.filesystem,
                    "total_bytes": p.total_bytes,
                    "free_bytes": p.free_bytes,
                }
                for p in snapshot.disk.partitions
            ]

    score_payload: dict[str, object] = {}
    if score is not None:
        score_payload = {
            "total": score.total,
            "grade": score.grade,
            "confidence": score.confidence,
            "coverage_percent": round(score.coverage * 100, 1),
            "summary": score.summary,
            "components": [
                {
                    "key": c.key,
                    "label": c.label,
                    "score": c.score,
                    "weight_percent": round(c.weight * 100, 1),
                    "available": c.available,
                    "detail": c.detail,
                }
                for c in score.components
            ],
            "methodology": list(METHODOLOGY),
        }

    recommendation_payload = tuple(
        {
            "rule_id": item.rule_id,
            "title": item.title,
            "severity": item.severity.value,
            "summary": item.summary,
            "explanation": item.explanation,
            "evidence": list(item.evidence),
            "confidence": item.confidence,
        }
        for item in recommendations
    )

    period_start = rows[0].ts if rows else (snapshot.timestamp if snapshot else None)
    period_end = rows[-1].ts if rows else (snapshot.timestamp if snapshot else None)

    return ReportData(
        generated_at=time.time(),
        period_start=period_start,
        period_end=period_end,
        system=system,
        metrics=summarize_rows(rows),
        score=score_payload,
        recommendations=recommendation_payload,
        missing=tuple(missing_metrics),
        notes=tuple(notes),
        include_hostname=include_hostname,
    )


def _display(value: float | None, unit: str) -> str:
    if value is None:
        return formatting.UNAVAILABLE
    if unit == "bytes":
        return formatting.format_bytes(value)
    if unit == "bytes/s":
        return formatting.format_rate(value)
    if unit == "%":
        return f"{value:.1f}%"
    if unit == "°C":
        return f"{value:.1f} °C"
    return f"{value:g} {unit}".strip()


def render_csv(report: ReportData) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["NEXUS performance report"])
    writer.writerow(["Generated", datetime.fromtimestamp(report.generated_at).isoformat(timespec="seconds")])
    if report.period_start is not None:
        writer.writerow(
            [
                "Collection period",
                f"{datetime.fromtimestamp(report.period_start).isoformat(timespec='seconds')} → "
                f"{datetime.fromtimestamp(report.period_end or report.period_start).isoformat(timespec='seconds')}",
            ]
        )
    writer.writerow([])
    writer.writerow(["System", "Value"])
    for key, value in report.system.items():
        writer.writerow([key, value])
    writer.writerow([])
    writer.writerow(["Metric", "Unit", "Minimum", "Maximum", "Average", "Samples"])
    for stat in report.metrics:
        writer.writerow(
            [
                stat.label,
                stat.unit,
                "" if stat.minimum is None else stat.minimum,
                "" if stat.maximum is None else stat.maximum,
                "" if stat.average is None else stat.average,
                stat.samples,
            ]
        )
    if report.score:
        writer.writerow([])
        writer.writerow(["Performance score", report.score.get("total"), report.score.get("grade")])
        writer.writerow(["Confidence", report.score.get("confidence")])
        writer.writerow(["Coverage %", report.score.get("coverage_percent")])
    if report.recommendations:
        writer.writerow([])
        writer.writerow(["Rule", "Severity", "Title", "Summary"])
        for rec in report.recommendations:
            writer.writerow([rec["rule_id"], rec["severity"], rec["title"], rec["summary"]])
    if report.missing:
        writer.writerow([])
        writer.writerow(["Unavailable metrics"])
        for item in report.missing:
            writer.writerow([item])
    return buffer.getvalue()


def render_json(report: ReportData) -> str:
    return json.dumps(report.to_dict(), indent=2, default=str)


def render_html(report: ReportData, *, include_notes: bool = True) -> str:
    generated = datetime.fromtimestamp(report.generated_at).strftime("%Y-%m-%d %H:%M:%S")
    system_rows = "".join(
        f"<tr><td style='color:#9CA3AF;padding:3px 10px 3px 0'>{html.escape(str(k))}</td>"
        f"<td style='padding:3px 0'>{html.escape(str(v))}</td></tr>"
        for k, v in report.system.items()
    )
    metric_rows = "".join(
        f"<tr><td style='padding:5px 8px'>{html.escape(s.label)}</td>"
        f"<td style='padding:5px 8px;color:#9CA3AF'>{html.escape(s.unit)}</td>"
        f"<td style='padding:5px 8px'>{html.escape(_display(s.minimum, s.unit))}</td>"
        f"<td style='padding:5px 8px'>{html.escape(_display(s.maximum, s.unit))}</td>"
        f"<td style='padding:5px 8px'>{html.escape(_display(s.average, s.unit))}</td>"
        f"<td style='padding:5px 8px;color:#9CA3AF'>{s.samples}</td></tr>"
        for s in report.metrics
    )
    score_html = ""
    if report.score:
        components = "".join(
            f"<tr><td style='padding:4px 8px'>{html.escape(str(c['label']))}</td>"
            f"<td style='padding:4px 8px'>{c['score'] if c['available'] else 'Unavailable'}</td>"
            f"<td style='padding:4px 8px;color:#9CA3AF'>{c['weight_percent']}%</td>"
            f"<td style='padding:4px 8px;color:#9CA3AF'>{html.escape(str(c['detail']))}</td></tr>"
            for c in report.score.get("components", [])  # type: ignore[union-attr]
        )
        score_html = f"""
        <h2 style="color:#F9FAFB;font-size:15px;margin-top:24px">Performance health score</h2>
        <p style="color:#F9FAFB;font-size:26px;margin:4px 0">{report.score.get('total')}/100
        <span style="font-size:13px;color:#9CA3AF">({html.escape(str(report.score.get('grade')))})</span></p>
        <p style="color:#9CA3AF;margin:0 0 8px 0">{html.escape(str(report.score.get('summary')))}
        · Confidence: {html.escape(str(report.score.get('confidence')))}
        · Data coverage: {report.score.get('coverage_percent')}%</p>
        <table cellspacing="0" cellpadding="0" width="100%" style="border-collapse:collapse">
        <tr><th align="left" style="padding:4px 8px;color:#9CA3AF;font-weight:normal">Component</th>
        <th align="left" style="padding:4px 8px;color:#9CA3AF;font-weight:normal">Score</th>
        <th align="left" style="padding:4px 8px;color:#9CA3AF;font-weight:normal">Weight</th>
        <th align="left" style="padding:4px 8px;color:#9CA3AF;font-weight:normal">Observation</th></tr>
        {components}</table>
        <p style="color:#6B7280;font-size:11px">This score estimates current resource pressure and system
        health; it is not a benchmark of computer speed.</p>
        """
    rec_html = ""
    if report.recommendations:
        items = "".join(
            f"<li style='margin-bottom:8px'><b>{html.escape(str(r['title']))}</b> "
            f"<span style='color:#9CA3AF'>[{html.escape(str(r['severity']))} · {html.escape(str(r['rule_id']))}]</span><br>"
            f"<span style='color:#D1D5DB'>{html.escape(str(r['summary']))}</span></li>"
            for r in report.recommendations
        )
        rec_html = (
            f"<h2 style='color:#F9FAFB;font-size:15px;margin-top:24px'>Recommendations</h2>"
            f"<ul style='color:#F9FAFB;padding-left:18px'>{items}</ul>"
        )
    missing_html = ""
    if report.missing:
        items = "".join(f"<li>{html.escape(m)}</li>" for m in report.missing)
        missing_html = (
            f"<h2 style='color:#F9FAFB;font-size:15px;margin-top:24px'>Unavailable metrics</h2>"
            f"<ul style='color:#9CA3AF'>{items}</ul>"
        )
    notes_html = ""
    if include_notes and report.notes:
        items = "".join(f"<li>{html.escape(n)}</li>" for n in report.notes)
        notes_html = (
            f"<h2 style='color:#F9FAFB;font-size:15px;margin-top:24px'>Notes</h2>"
            f"<ul style='color:#9CA3AF'>{items}</ul>"
        )
    period = ""
    if report.period_start is not None:
        start = datetime.fromtimestamp(report.period_start).strftime("%Y-%m-%d %H:%M:%S")
        end = datetime.fromtimestamp(report.period_end or report.period_start).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        period = f"<p style='color:#9CA3AF;margin:2px 0'>Collection period: {start} → {end}</p>"

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>NEXUS performance report</title></head>
<body style="background:#0B0F19;color:#F9FAFB;font-family:'Segoe UI',Arial,sans-serif;padding:24px">
<h1 style="font-size:22px;margin:0">NEXUS performance report</h1>
<p style="color:#9CA3AF;margin:4px 0 0 0">Generated {generated} · NEXUS {html.escape(report.app_version)}</p>
{period}
<h2 style="color:#F9FAFB;font-size:15px;margin-top:24px">System</h2>
<table cellspacing="0" cellpadding="0" style="border-collapse:collapse">{system_rows}</table>
{score_html}
<h2 style="color:#F9FAFB;font-size:15px;margin-top:24px">Observed metrics</h2>
<table cellspacing="0" cellpadding="0" width="100%" style="border-collapse:collapse">
<tr><th align="left" style="padding:5px 8px;color:#9CA3AF;font-weight:normal;border-bottom:1px solid #1F2937">Metric</th>
<th align="left" style="padding:5px 8px;color:#9CA3AF;font-weight:normal;border-bottom:1px solid #1F2937">Unit</th>
<th align="left" style="padding:5px 8px;color:#9CA3AF;font-weight:normal;border-bottom:1px solid #1F2937">Minimum</th>
<th align="left" style="padding:5px 8px;color:#9CA3AF;font-weight:normal;border-bottom:1px solid #1F2937">Maximum</th>
<th align="left" style="padding:5px 8px;color:#9CA3AF;font-weight:normal;border-bottom:1px solid #1F2937">Average</th>
<th align="left" style="padding:5px 8px;color:#9CA3AF;font-weight:normal;border-bottom:1px solid #1F2937">Samples</th></tr>
{metric_rows}</table>
{rec_html}
{missing_html}
{notes_html}
<p style="color:#6B7280;font-size:11px;margin-top:28px">Generated locally by NEXUS. No data was uploaded.</p>
</body></html>"""


def suggested_filename(extension: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"nexus-report-{stamp}.{extension.lstrip('.')}"
