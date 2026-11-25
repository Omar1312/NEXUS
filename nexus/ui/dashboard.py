"""Dashboard: live CPU, GPU, memory, disk and network overview."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout

from nexus.core.metrics import Snapshot
from nexus.ui import theme
from nexus.ui.base import BasePage
from nexus.ui.widgets.charts import CoreBars, TimeSeriesChart, UsageBar
from nexus.ui.widgets.common import (
    Banner,
    Card,
    MetricCard,
    PageScroll,
    StatsRow,
    StatTile,
)
from nexus.utils import formatting
from nexus.platforms.selection import platform_id, architecture_id


def _level_color(percent: float | None, warn: float = 85.0, crit: float = 95.0) -> str:
    palette = theme.current_palette()
    if percent is None:
        return palette.accent
    if percent >= crit:
        return palette.critical
    if percent >= warn:
        return palette.warning
    return palette.accent


class DashboardPage(BasePage):
    title = "Dashboard"
    subtitle = "Live performance overview of this computer"

    def __init__(self, context) -> None:
        super().__init__(context)
        palette = theme.current_palette()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = PageScroll()
        root.addWidget(scroll)
        content = scroll.content_layout

        self.banner = Banner("", level="warning")
        self.banner.setVisible(False)
        content.addWidget(self.banner)

        tiles_row = QHBoxLayout()
        tiles_row.setSpacing(12)
        self.os_tile = StatTile("Operating system", "—", "Detecting…")
        self.cpu_tile = StatTile("Processor", "—", "Detecting…")
        self.memory_tile = StatTile("Installed memory", "—", "Detecting…")
        self.uptime_tile = StatTile("System uptime", "—", "Since last boot")
        for tile in (self.os_tile, self.cpu_tile, self.memory_tile, self.uptime_tile):
            tiles_row.addWidget(tile, 1)
        content.addLayout(tiles_row)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        content.addLayout(grid, 1)

        max_points = context.settings.current.chart_history_points

        # CPU -----------------------------------------------------------------
        self.cpu_card = MetricCard("CPU", "cpu", unit="%")
        self.cpu_card.set_value("—", "%")
        self.cpu_cores = CoreBars()
        self.cpu_chart = TimeSeriesChart(
            [("CPU", palette.accent)], max_points=max_points, y_max=100, height=104, fill=True
        )
        self.cpu_card.add_content(self.cpu_cores)
        self.cpu_card.add_content(self.cpu_chart)
        grid.addWidget(self.cpu_card, 0, 0)

        # GPU -----------------------------------------------------------------
        self.gpu_card = MetricCard("GPU", "gpu", unit="%")
        self.gpu_card.set_value("—", "%")
        self.gpu_stats = StatsRow(["VRAM", "Temperature", "Power", "Fan"])
        self.gpu_card.add_content(self.gpu_stats)
        self.gpu_chart = TimeSeriesChart(
            [("GPU", palette.success)], max_points=max_points, y_max=100, height=96, fill=True
        )
        self.gpu_card.add_content(self.gpu_chart)
        grid.addWidget(self.gpu_card, 0, 1)

        # Memory --------------------------------------------------------------
        self.memory_card = MetricCard("Memory", "ram", unit="%")
        self.memory_chart = TimeSeriesChart(
            [("Memory", palette.warning)], max_points=max_points, y_max=100, height=100, fill=True
        )
        self.memory_card.add_content(self.memory_chart)
        grid.addWidget(self.memory_card, 1, 0)

        # Disk ----------------------------------------------------------------
        self.disk_card = MetricCard("System volume", "storage", unit="free")
        self.disk_bar = UsageBar()
        self.disk_bar.setFixedHeight(6)
        self.disk_stats = StatsRow(["Read", "Write", "Activity", "Capacity"])
        self.disk_card.add_content(self.disk_bar)
        self.disk_card.add_content(self.disk_stats)
        self.disk_chart = TimeSeriesChart(
            [("Read", palette.accent), ("Write", palette.success)],
            max_points=max_points,
            y_max=None,
            height=92,
            formatter=lambda value: formatting.format_rate(value),
        )
        self.disk_card.add_content(self.disk_chart)
        grid.addWidget(self.disk_card, 1, 1)

        # Network -------------------------------------------------------------
        self.network_card = MetricCard("Network", "network", unit="")
        self.network_stats = StatsRow(["Upload", "Interface", "Link speed", "Session total"])
        self.network_card.add_content(self.network_stats)
        self.network_chart = TimeSeriesChart(
            [("Download", palette.accent), ("Upload", palette.warning)],
            max_points=max_points,
            y_max=None,
            height=104,
            formatter=lambda value: formatting.format_rate(value),
        )
        self.network_card.add_content(self.network_chart)
        grid.addWidget(self.network_card, 2, 0, 1, 2)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)
        content.addStretch(1)

        self.context.settings.changed.connect(self._on_settings_changed)
        latest = context.monitoring.latest
        if latest is not None:
            self.on_snapshot(latest)

    # -- lifecycle ----------------------------------------------------------
    def on_activated(self) -> None:
        latest = self.context.monitoring.latest
        if latest is not None:
            self.on_snapshot(latest)

    def on_snapshot(self, snapshot: Snapshot) -> None:
        self._update_system(snapshot)
        self._update_cpu(snapshot)
        self._update_gpu(snapshot)
        self._update_memory(snapshot)
        self._update_disk(snapshot)
        self._update_network(snapshot)
        self._update_warnings(snapshot)

    def refresh_theme(self) -> None:
        self.cpu_card.refresh_theme()
        self.gpu_card.refresh_theme()
        self.memory_card.refresh_theme()
        self.disk_card.refresh_theme()
        self.network_card.refresh_theme()
        for chart in (self.cpu_chart, self.gpu_chart, self.memory_chart, self.disk_chart, self.network_chart):
            chart.apply_theme()
        latest = self.context.monitoring.latest
        if latest is not None:
            self.on_snapshot(latest)

    def _on_settings_changed(self, settings) -> None:
        for chart in (self.cpu_chart, self.gpu_chart, self.memory_chart, self.disk_chart, self.network_chart):
            chart.set_max_points(settings.chart_history_points)

    # -- section updates ----------------------------------------------------
    def _update_system(self, snapshot: Snapshot) -> None:
        info = snapshot.system
        if info is not None:
            self.os_tile.set_value(info.os_name or "Unknown OS", f"Build {info.os_build or '—'} · {info.architecture}")
            self.uptime_tile.set_value(
                formatting.format_duration(info.uptime_seconds), "Since last boot"
            )
        cpu = snapshot.cpu
        if cpu is not None:
            self.cpu_tile.set_value(
                _short_cpu_name(cpu.model),
                f"{cpu.physical_cores or '—'} cores · {cpu.logical_cores or '—'} threads",
            )
        memory = snapshot.memory
        if memory is not None:
            self.memory_tile.set_value(
                formatting.format_bytes(memory.total_bytes, precision=1),
                (f"{formatting.format_bytes(memory.available_bytes)} available ? Unified memory shared with GPU"
                 if platform_id() == "macos" and architecture_id() == "arm64"
                 else f"{formatting.format_bytes(memory.available_bytes)} available"),
            )

    def _update_cpu(self, snapshot: Snapshot) -> None:
        cpu = snapshot.cpu
        if cpu is None:
            self.cpu_card.set_value("—", "%")
            self.cpu_card.set_subtitle("CPU metrics unavailable.")
            return
        utilization = cpu.utilization_percent
        self.cpu_card.set_value(
            f"{utilization:.0f}" if utilization is not None else "—", "%"
        )
        frequency = formatting.format_frequency(cpu.frequency_mhz)
        subtitle = f"{cpu.model} · {cpu.physical_cores or '—'}C/{cpu.logical_cores or '—'}T"
        if frequency != formatting.UNAVAILABLE:
            subtitle += f" · {frequency}"
        self.cpu_card.set_subtitle(subtitle)
        if cpu.temperature_c is not None:
            self.cpu_card.set_badge(f"{cpu.temperature_c:.0f} °C", "success" if cpu.temperature_c < 80 else "warning")
        else:
            self.cpu_card.set_badge("No temp sensor", "neutral")
            self.cpu_card.setToolTip(
                "CPU temperature is unavailable from the supported sensor interfaces on this platform."
                if platform_id() == "macos" else
                "Windows does not expose CPU temperature. Install LibreHardwareMonitor "
                "to publish it through WMI if you want this reading."
            )
        self.cpu_card.set_progress(utilization, _level_color(utilization))
        self.cpu_cores.set_values(cpu.per_core_percent)
        if utilization is not None:
            self.cpu_chart.append(snapshot.timestamp, {"CPU": utilization})

    def _update_gpu(self, snapshot: Snapshot) -> None:
        gpu = snapshot.gpus[0] if snapshot.gpus else None
        if gpu is None:
            self.gpu_card.set_value("—", "")
            self.gpu_card.set_subtitle(
                ("GPU utilization and dedicated GPU memory are not exposed by the supported macOS interfaces. "
                 "Apple Silicon uses the unified memory shown on this dashboard.")
                if platform_id() == "macos" else
                "No NVIDIA GPU with NVML support was detected. GPU metrics are shown only when the driver exposes them."
            )
            self.gpu_card.set_progress(None)
            self.gpu_card.set_badge("Unavailable", "neutral")
            self.gpu_stats.set_values(
                {"VRAM": "Unavailable", "Temperature": "Unavailable", "Power": "Unavailable", "Fan": "Unavailable"}
            )
            return
        if gpu.utilization_percent is not None:
            self.gpu_card.set_value(f"{gpu.utilization_percent:.0f}", "%")
        else:
            self.gpu_card.set_value("—", "")
        subtitle = gpu.name
        if gpu.driver_version:
            subtitle += f" · driver {gpu.driver_version}"
        self.gpu_card.set_subtitle(subtitle)
        self.gpu_card.set_progress(gpu.utilization_percent, _level_color(gpu.utilization_percent, 85, 95))
        self.gpu_stats.set_values(
            {
                "VRAM": (
                    f"{formatting.format_bytes(gpu.memory_used_bytes)} / "
                    f"{formatting.format_bytes(gpu.memory_total_bytes)}"
                    if gpu.memory_total_bytes
                    else "Unavailable"
                ),
                "Temperature": formatting.format_temperature(gpu.temperature_c),
                "Power": formatting.format_power(gpu.power_watts),
                "Fan": formatting.format_percent(gpu.fan_percent),
            }
        )
        if gpu.temperature_c is None:
            self.gpu_card.set_badge("No temp", "neutral")
        elif gpu.temperature_c >= 85:
            self.gpu_card.set_badge(f"{gpu.temperature_c:.0f} °C", "warning")
        else:
            self.gpu_card.set_badge(f"{gpu.temperature_c:.0f} °C", "success")
        if gpu.utilization_percent is not None:
            self.gpu_chart.append(snapshot.timestamp, {"GPU": gpu.utilization_percent})

    def _update_memory(self, snapshot: Snapshot) -> None:
        memory = snapshot.memory
        if memory is None:
            self.memory_card.set_value("—", "%")
            self.memory_card.set_subtitle("Memory metrics unavailable.")
            return
        threshold = self.context.settings.current.memory_warning_threshold
        self.memory_card.set_value(f"{memory.percent:.0f}", "%")
        self.memory_card.set_subtitle(
            f"{formatting.format_bytes(memory.used_bytes)} used of "
            f"{formatting.format_bytes(memory.total_bytes)} · "
            f"{formatting.format_bytes(memory.available_bytes)} available"
        )
        self.memory_card.set_progress(memory.percent, _level_color(memory.percent, threshold, 96))
        if memory.swap_total_bytes:
            self.memory_card.set_badge(
                f"{'Swap' if platform_id() == 'macos' else 'Page file'} {formatting.format_bytes(memory.swap_used_bytes)} used", "neutral"
            )
        self.memory_chart.append(snapshot.timestamp, {"Memory": memory.percent})

    def _update_disk(self, snapshot: Snapshot) -> None:
        disk = snapshot.disk
        if disk is None or not disk.partitions:
            self.disk_card.set_value("—", "")
            self.disk_card.set_subtitle("No accessible volume was found.")
            self.disk_stats.set_values(
                {"Read": "Unavailable", "Write": "Unavailable", "Activity": "Unavailable", "Capacity": "—"}
            )
            return
        primary = max(disk.partitions, key=lambda p: p.total_bytes)
        free_gib = primary.free_bytes / (1024**3)
        self.disk_card.set_value(f"{free_gib:.0f}", "GiB free")
        self.disk_card.set_subtitle(
            f"{primary.mountpoint} · {primary.filesystem} · "
            f"{formatting.format_bytes(primary.used_bytes)} used of "
            f"{formatting.format_bytes(primary.total_bytes)}"
        )
        used_percent = primary.percent_used
        threshold = self.context.settings.current.storage_warning_threshold
        free_percent = 100.0 - used_percent
        self.disk_bar.set_percent(used_percent)
        badge_level = "critical" if free_percent < threshold / 2 else ("warning" if free_percent < threshold else "success")
        self.disk_card.set_badge(f"{free_percent:.0f}% free", badge_level)
        self.disk_stats.set_values(
            {
                "Read": formatting.format_rate(disk.read_bytes_per_sec),
                "Write": formatting.format_rate(disk.write_bytes_per_sec),
                "Activity": formatting.format_percent(disk.activity_percent),
                "Capacity": f"{len(disk.partitions)} volume{'s' if len(disk.partitions) != 1 else ''}",
            }
        )
        if disk.read_bytes_per_sec is not None or disk.write_bytes_per_sec is not None:
            self.disk_chart.append(
                snapshot.timestamp,
                {
                    "Read": disk.read_bytes_per_sec,
                    "Write": disk.write_bytes_per_sec,
                },
            )

    def _update_network(self, snapshot: Snapshot) -> None:
        network = snapshot.network
        if network is None:
            self.network_card.set_value("—", "")
            self.network_card.set_subtitle("Network metrics unavailable.")
            return
        download = network.download_bytes_per_sec
        self.network_card.set_value(formatting.format_rate(download), "")
        self.network_card.set_subtitle(
            f"{network.interface or 'No active adapter'} · "
            f"{formatting.format_bitrate(download)} down · "
            f"{formatting.format_bitrate(network.upload_bytes_per_sec)} up"
        )
        if download is not None and network.link_speed_mbps:
            self.network_card.set_progress(
                min(100.0, 100.0 * (download * 8) / (network.link_speed_mbps * 1_000_000)),
                theme.current_palette().accent,
            )
        else:
            self.network_card.set_progress(None)
        self.network_stats.set_values(
            {
                "Upload": formatting.format_rate(network.upload_bytes_per_sec),
                "Interface": network.interface or "Unavailable",
                "Link speed": (
                    f"{network.link_speed_mbps:.0f} Mbit/s" if network.link_speed_mbps else "Unavailable"
                ),
                "Session total": (
                    f"↓ {formatting.format_bytes(network.total_received_bytes)} · "
                    f"↑ {formatting.format_bytes(network.total_sent_bytes)}"
                ),
            }
        )
        if download is not None or network.upload_bytes_per_sec is not None:
            self.network_chart.append(
                snapshot.timestamp,
                {
                    "Download": download,
                    "Upload": network.upload_bytes_per_sec,
                },
            )
        self.network_card.set_badge(
            "Connected" if network.interface else "No adapter",
            "success" if network.interface else "warning",
        )

    def _update_warnings(self, snapshot: Snapshot) -> None:
        if snapshot.warnings:
            self.banner.text_label.setText(" · ".join(snapshot.warnings))
            self.banner.setVisible(True)
        else:
            self.banner.setVisible(False)


def _short_cpu_name(name: str) -> str:
    cleaned = name.replace("(R)", "").replace("(TM)", "").replace("CPU ", "").strip()
    cleaned = " ".join(cleaned.split())
    if len(cleaned) > 28:
        return cleaned[:27] + "…"
    return cleaned
