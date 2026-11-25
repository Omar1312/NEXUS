"""Gaming Mode: manual session recording with real resource metrics only."""

from __future__ import annotations

import html
import json
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from nexus.core.gaming_session import GamingSample, GamingSessionRecorder, GamingSummary
from nexus.core.process_manager import top_processes
from nexus.services.background_task import BackgroundTask
from nexus.ui import theme
from nexus.ui.base import BasePage
from nexus.ui.widgets.charts import TimeSeriesChart
from nexus.ui.widgets.common import (
    Badge,
    Banner,
    Card,
    PageScroll,
    SectionHeader,
    StatsRow,
    StatTile,
)
from nexus.ui.widgets.table import Column, RecordsModel, configure_table
from nexus.utils import formatting
from nexus.platforms.selection import platform_id, architecture_id

FPS_NOTE = (
    "NEXUS does not measure in-game FPS and does not inject into games. Session "
    "recording covers system CPU, GPU, memory, VRAM and available sensors only."
)


class GamingPage(BasePage):
    title = "Gaming Mode"
    subtitle = "Record a session and review real resource behaviour"

    def __init__(self, context) -> None:
        super().__init__(context)
        palette = theme.current_palette()
        self._summary: GamingSummary | None = None
        self._summary_samples: tuple[GamingSample, ...] = ()
        self._session_start: float | None = None
        self._processes = []
        self._tasks: list[BackgroundTask] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = PageScroll()
        root.addWidget(scroll)
        content = scroll.content_layout

        control = Card("Session control")
        control_row = QHBoxLayout()
        control_row.setSpacing(16)
        status_box = QVBoxLayout()
        status_box.setSpacing(2)
        self.status_badge = Badge("Idle", "neutral")
        self.status_badge.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.timer_label = QLabel("00:00:00")
        self.timer_label.setStyleSheet("font-size: 26pt; font-weight: 650; letter-spacing: 1px;")
        self.session_note = QLabel(
            "Start a session before launching a game. Data stays local and is saved when you stop."
        )
        self.session_note.setObjectName("muted")
        self.session_note.setWordWrap(True)
        status_box.addWidget(self.status_badge)
        status_box.addWidget(self.timer_label)
        status_box.addWidget(self.session_note)
        control_row.addLayout(status_box, 1)
        self.start_button = QPushButton("Start session")
        self.start_button.setObjectName("primary")
        self.start_button.setMinimumWidth(130)
        self.start_button.clicked.connect(self._start_session)
        self.stop_button = QPushButton("Stop session")
        self.stop_button.setObjectName("danger")
        self.stop_button.setMinimumWidth(130)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self._stop_session)
        control_row.addWidget(self.start_button)
        control_row.addWidget(self.stop_button)
        control.body.addLayout(control_row)

        self.session_banner = Banner(FPS_NOTE, level="info", icon_name="info")
        control.body.addWidget(self.session_banner)
        content.addWidget(control)

        tiles = QHBoxLayout()
        tiles.setSpacing(12)
        self.cpu_tile = StatTile("CPU", "—", "Live utilization")
        self.gpu_tile = StatTile("GPU", "—", "NVIDIA NVML")
        self.ram_tile = StatTile("Memory", "—", "Physical RAM")
        self.vram_tile = StatTile("VRAM", "—", "GPU memory")
        self.temp_tile = StatTile("GPU temperature", "—", "Sensor dependent")
        for tile in (self.cpu_tile, self.gpu_tile, self.ram_tile, self.vram_tile, self.temp_tile):
            tiles.addWidget(tile, 1)
        content.addLayout(tiles)

        charts = Card("Live resource trends")
        self.trend_chart = TimeSeriesChart(
            [("CPU", palette.accent), ("GPU", palette.success)],
            max_points=300,
            y_max=100,
            height=170,
        )
        charts.body.addWidget(self.trend_chart)
        content.addWidget(charts)

        memory_chart_card = Card("Memory and GPU memory")
        self.memory_chart = TimeSeriesChart(
            [("System memory", palette.warning), ("GPU memory", palette.accent)],
            max_points=300,
            y_max=100,
            height=140,
        )
        memory_chart_card.body.addWidget(self.memory_chart)
        content.addWidget(memory_chart_card)

        processes_card = Card("Background resource users")
        processes_card.add_header_widget(QLabel("Top CPU consumers right now"))
        self.process_model = RecordsModel(
            [
                Column("Process", lambda p: p.name, width=220),
                Column(
                    "PID",
                    lambda p: p.pid,
                    width=70,
                    align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                ),
                Column(
                    "CPU",
                    lambda p: p.cpu_percent,
                    formatter=lambda v: f"{v:.1f}%",
                    width=80,
                    align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                ),
                Column(
                    "Memory",
                    lambda p: p.memory_rss,
                    formatter=formatting.format_bytes,
                    width=100,
                    align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                ),
            ]
        )
        self.process_table = QTableView()
        configure_table(self.process_table, self.process_model)
        self.process_table.setSortingEnabled(False)
        self.process_table.setMinimumHeight(170)
        processes_card.body.addWidget(self.process_table)
        content.addWidget(processes_card)

        self.summary_card = Card("Session summary")
        self.summary_card.setVisible(False)
        self.summary_title = QLabel("—")
        self.summary_title.setStyleSheet("font-size: 12pt; font-weight: 650;")
        self.summary_card.body.addWidget(self.summary_title)
        self.summary_grid = StatsRow(
            ["Average CPU", "Peak CPU", "Average GPU", "Peak GPU", "Peak memory", "Peak VRAM", "GPU temp avg", "GPU temp max"],
            columns=4,
        )
        self.summary_card.body.addWidget(self.summary_grid)
        self.summary_missing = QLabel("")
        self.summary_missing.setObjectName("faint")
        self.summary_missing.setWordWrap(True)
        self.summary_card.body.addWidget(self.summary_missing)
        actions = QHBoxLayout()
        self.export_button = QPushButton("Export session report")
        self.export_button.setObjectName("ghost")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self._export_report)
        actions.addWidget(self.export_button)
        actions.addStretch(1)
        self.saved_label = QLabel("")
        self.saved_label.setObjectName("faint")
        actions.addWidget(self.saved_label)
        self.summary_card.body.addLayout(actions)
        content.addWidget(self.summary_card)

        sessions_header = SectionHeader("Recent sessions", "Sessions saved in the local database.")
        self.sessions_card = Card()
        self.sessions_card.body.addWidget(sessions_header)
        self.sessions_model = RecordsModel(
            [
                Column(
                    "Started",
                    lambda s: s["started_at"],
                    formatter=lambda v: formatting.format_timestamp(v),
                    width=170,
                ),
                Column(
                    "Duration",
                    lambda s: s["duration_seconds"],
                    formatter=formatting.format_duration,
                    width=110,
                ),
                Column(
                    "Avg CPU",
                    lambda s: s["cpu_average"],
                    formatter=lambda v: f"{v:.0f}%" if v is not None else "Unavailable",
                    width=90,
                ),
                Column(
                    "Peak CPU",
                    lambda s: s["cpu_peak"],
                    formatter=lambda v: f"{v:.0f}%" if v is not None else "Unavailable",
                    width=90,
                ),
                Column(
                    "Avg GPU",
                    lambda s: s["gpu_average"],
                    formatter=lambda v: f"{v:.0f}%" if v is not None else "Unavailable",
                    width=90,
                ),
                Column(
                    "Peak memory",
                    lambda s: s["memory_peak_percent"],
                    formatter=lambda v: f"{v:.0f}%" if v is not None else "Unavailable",
                    width=110,
                ),
                Column("Samples", lambda s: s["sample_count"], width=80),
            ]
        )
        self.sessions_table = QTableView()
        configure_table(self.sessions_table, self.sessions_model)
        self.sessions_table.setMinimumHeight(150)
        self.sessions_card.body.addWidget(self.sessions_table)
        content.addWidget(self.sessions_card)
        content.addStretch(1)

        self.context.processes.sampleReady.connect(self._on_processes)
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick_timer)
        self._refresh_sessions()

    # -- lifecycle ----------------------------------------------------------
    def on_activated(self) -> None:
        self.context.processes.set_active(True)
        self._refresh_sessions()
        latest = self.context.monitoring.latest
        if latest is not None:
            self.on_snapshot(latest)

    def on_deactivated(self) -> None:
        self.context.processes.set_active(False)

    def refresh_now(self) -> None:
        self.context.monitoring.refresh_now()
        self.context.processes.refresh_now()

    def refresh_theme(self) -> None:
        self.trend_chart.apply_theme()
        self.memory_chart.apply_theme()

    # -- session ------------------------------------------------------------
    def _start_session(self) -> None:
        self.context.gaming.start()
        self._session_start = time.time()
        self._summary = None
        self.trend_chart.clear()
        self.memory_chart.clear()
        self.summary_card.setVisible(False)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_badge.setText("Recording")
        self.status_badge.set_level("success")
        self.session_note.setText(
            "Recording resource metrics locally. Nothing is uploaded and no game process is touched."
        )
        self._timer.start()
        self._tick_timer()

    def _stop_session(self) -> None:
        if not self.context.gaming.active:
            return
        summary = self.context.gaming.stop()
        self._summary = summary
        self._summary_samples = self.context.gaming.samples
        self._timer.stop()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_badge.setText("Stopped")
        self.status_badge.set_level("neutral")
        self.session_note.setText("Session stopped. Summary below is complete.")
        self._render_summary(summary)
        self._save_session(summary)

    def _tick_timer(self) -> None:
        if self._session_start is None:
            return
        elapsed = int(max(0, time.time() - self._session_start))
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.timer_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")

    def _render_summary(self, summary: GamingSummary) -> None:
        self.summary_card.setVisible(True)
        self.summary_title.setText(
            f"Session · {formatting.format_timestamp(self._session_start or time.time())} · "
            f"{formatting.format_duration(summary.duration_seconds)} · {summary.sample_count} samples"
        )
        self.summary_grid.set_values(
            {
                "Average CPU": _pct(summary.cpu_average),
                "Peak CPU": _pct(summary.cpu_peak),
                "Average GPU": _pct(summary.gpu_average),
                "Peak GPU": _pct(summary.gpu_peak),
                "Peak memory": _pct(summary.memory_peak_percent),
                "Peak VRAM": _pct(summary.vram_peak_percent),
                "GPU temp avg": formatting.format_temperature(summary.gpu_temperature_average),
                "GPU temp max": formatting.format_temperature(summary.gpu_temperature_max),
            }
        )
        missing = ", ".join(summary.missing_metrics)
        self.summary_missing.setText(
            f"Unavailable this session: {missing}." if missing else
            "All tracked sensors produced data during this session."
        )
        self.export_button.setEnabled(summary.sample_count > 0)

    def _save_session(self, summary: GamingSummary) -> None:
        try:
            self.context.repository.save_gaming_session(
                self._session_start or time.time(),
                time.time(),
                summary.to_dict(),
                self.context.gaming.samples_payload(),
            )
            self.saved_label.setText("Saved locally to the history database.")
            self._refresh_sessions()
        except Exception as exc:
            self.saved_label.setText("Session could not be saved to the database.")
            window = self.window()
            if hasattr(window, "show_toast"):
                window.show_toast(f"Session could not be saved: {exc}", "error")

    def _refresh_sessions(self) -> None:
        try:
            rows = self.context.repository.list_gaming_sessions(limit=20)
        except Exception:
            rows = []
        records: list[dict] = []
        for row in rows:
            try:
                summary = json.loads(row.summary_json or "{}")
            except json.JSONDecodeError:
                summary = {}
            records.append(
                {
                    "started_at": row.started_at,
                    "duration_seconds": summary.get("duration_seconds"),
                    "cpu_average": summary.get("cpu_average"),
                    "cpu_peak": summary.get("cpu_peak"),
                    "gpu_average": summary.get("gpu_average"),
                    "gpu_peak": summary.get("gpu_peak"),
                    "memory_peak_percent": summary.get("memory_peak_percent"),
                    "sample_count": summary.get("sample_count", 0),
                    "samples_json": row.samples_json,
                    "summary_json": row.summary_json,
                    "ended_at": row.ended_at,
                }
            )
        self.sessions_model.set_records(records)

    # -- live data ----------------------------------------------------------
    def on_snapshot(self, snapshot) -> None:
        cpu = snapshot.cpu.utilization_percent if snapshot.cpu else None
        gpu = snapshot.gpus[0] if snapshot.gpus else None
        gpu_util = gpu.utilization_percent if gpu else None
        ram = snapshot.memory.percent if snapshot.memory else None
        vram = gpu.memory_percent if gpu else None
        temp = gpu.temperature_c if gpu else None
        self.cpu_tile.set_value(_pct(cpu), "Live utilization")
        self.gpu_tile.set_value(_pct(gpu_util), gpu.name if gpu else ("GPU sensors unavailable on macOS" if platform_id() == "macos" else "No supported GPU"))
        self.ram_tile.set_value(_pct(ram), (
            f"{formatting.format_bytes(snapshot.memory.used_bytes)} of "
            f"{formatting.format_bytes(snapshot.memory.total_bytes)}"
            if snapshot.memory else "Unavailable"
        ))
        self.vram_tile.set_value(
            _pct(vram),
            (
                f"{formatting.format_bytes(gpu.memory_used_bytes)} / {formatting.format_bytes(gpu.memory_total_bytes)}"
                if gpu and gpu.memory_total_bytes else "Unavailable"
            ),
        )
        self.temp_tile.set_value(
            formatting.format_temperature(temp),
            "Unavailable" if temp is None else "Driver sensor",
        )
        self.trend_chart.append(snapshot.timestamp, {"CPU": cpu, "GPU": gpu_util})
        self.memory_chart.append(snapshot.timestamp, {"System memory": ram, "GPU memory": vram})
        if self.context.gaming.active:
            self.context.gaming.add_snapshot(snapshot)

    def _on_processes(self, processes) -> None:
        self._processes = processes
        heaviest = top_processes(processes, key="cpu", limit=8)
        self.process_model.set_records(heaviest)

    # -- export -------------------------------------------------------------
    def _export_report(self) -> None:
        if self._summary is None:
            return
        settings = self.context.settings.current
        default_dir = Path(settings.gaming_report_dir or settings.export_dir)
        try:
            default_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            default_dir = Path.home()
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export session report",
            str(default_dir / f"nexus-gaming-{stamp}.html"),
            "HTML report (*.html)",
        )
        if not path:
            return
        try:
            Path(path).write_text(self._render_report_html(), encoding="utf-8")
        except OSError as exc:
            window = self.window()
            if hasattr(window, "show_toast"):
                window.show_toast(f"Report could not be written: {exc}", "error")
            return
        window = self.window()
        if hasattr(window, "show_toast"):
            window.show_toast(f"Session report saved to {path}", "success")

    def _render_report_html(self) -> str:
        summary = self._summary
        if summary is None:
            return ""
        rows = "".join(
            f"<tr><td>{html.escape(label)}</td><td align='right'>{html.escape(value)}</td></tr>"
            for label, value in (
                ("Duration", formatting.format_duration(summary.duration_seconds)),
                ("Samples", str(summary.sample_count)),
                ("Average CPU", _pct(summary.cpu_average)),
                ("Peak CPU", _pct(summary.cpu_peak)),
                ("Average GPU", _pct(summary.gpu_average)),
                ("Peak GPU", _pct(summary.gpu_peak)),
                ("Peak memory", _pct(summary.memory_peak_percent)),
                ("Peak VRAM", _pct(summary.vram_peak_percent)),
                ("GPU temperature average", formatting.format_temperature(summary.gpu_temperature_average)),
                ("GPU temperature maximum", formatting.format_temperature(summary.gpu_temperature_max)),
            )
        )
        samples = self._summary_samples[:: max(1, len(self._summary_samples) // 300)] if self._summary_samples else []
        sample_rows = "".join(
            f"<tr><td>{formatting.format_time_short(sample.ts)}</td>"
            f"<td align='right'>{_pct(sample.cpu_percent)}</td>"
            f"<td align='right'>{_pct(sample.gpu_percent)}</td>"
            f"<td align='right'>{_pct(sample.memory_percent)}</td>"
            f"<td align='right'>{formatting.format_temperature(sample.gpu_temperature_c)}</td></tr>"
            for sample in samples
        )
        missing = ", ".join(summary.missing_metrics) or "None"
        started = formatting.format_timestamp(self._session_start or time.time())
        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>NEXUS gaming session report</title></head>
<body style="background:#0B0F19;color:#F9FAFB;font-family:'Segoe UI',Arial,sans-serif;padding:24px">
<h1 style="font-size:20px;margin:0">NEXUS gaming session report</h1>
<p style="color:#9CA3AF;margin:4px 0 18px 0">Started {html.escape(started)} · generated locally</p>
<table cellspacing="0" cellpadding="4" style="border-collapse:collapse">{rows}</table>
<p style="color:#9CA3AF;margin-top:14px">Unavailable metrics: {html.escape(missing)}</p>
<h2 style="font-size:15px;margin-top:22px">Timeline (downsampled)</h2>
<table cellspacing="0" cellpadding="4" width="100%" style="border-collapse:collapse">
<tr style="color:#9CA3AF"><th align="left">Time</th><th align="right">CPU</th><th align="right">GPU</th><th align="right">RAM</th><th align="right">GPU temp</th></tr>
{sample_rows}</table>
<p style="color:#6B7280;font-size:11px;margin-top:24px">NEXUS does not measure in-game FPS and does not interact with games or anti-cheat software.</p>
</body></html>"""


def _pct(value: float | None) -> str:
    return "Unavailable" if value is None else f"{value:.0f}%"
