"""Hardware Monitor: capability detection, static details and live sensors."""

from __future__ import annotations

import time
from dataclasses import dataclass, replace

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from nexus.core.metrics import (
    Capability,
    RunningStats,
    Snapshot,
    SensorReading,
    snapshot_readings,
)
from nexus.ui import theme
from nexus.ui.base import BasePage
from nexus.ui.widgets.common import (
    Badge,
    Card,
    PageScroll,
    SectionHeader,
    StatsRow,
)
from nexus.ui.widgets.table import Column, RecordsModel, configure_table
from nexus.utils import formatting
from nexus.platforms.selection import platform_id, architecture_id

UNIT_LABELS = {"%": "%", "B": "bytes", "B/s": "per second", "MHz": "MHz", "°C": "°C", "W": "W"}


def _format_value(value: float | None, unit: str) -> str:
    if value is None:
        return "Unavailable"
    if unit == "%":
        return f"{value:.1f}%" if value % 1 else f"{value:.0f}%"
    if unit == "B":
        return formatting.format_bytes(value)
    if unit == "B/s":
        return formatting.format_rate(value)
    if unit == "MHz":
        return formatting.format_frequency(value)
    if unit == "°C":
        return formatting.format_temperature(value)
    if unit == "W":
        return formatting.format_power(value)
    return f"{value:g} {unit}".strip()


@dataclass(frozen=True, slots=True)
class SensorRow:
    key: str
    category: str
    label: str
    unit: str
    value: float | None
    minimum: float | None
    maximum: float | None
    average: float | None
    samples: int
    note: str


class SensorTableModel(QAbstractTableModel):
    HEADERS = ("Sensor", "Current", "Minimum", "Maximum", "Average", "Status")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._rows: list[SensorRow] = []

    @property
    def rows(self) -> list[SensorRow]:
        return self._rows

    def update_rows(self, rows: list[SensorRow]) -> None:
        keys = [row.key for row in rows]
        existing = [row.key for row in self._rows]
        if keys != existing:
            self.beginResetModel()
            self._rows = rows
            self.endResetModel()
        else:
            self._rows = rows
            if rows:
                self.dataChanged.emit(
                    self.index(0, 0), self.index(len(rows) - 1, len(self.HEADERS) - 1)
                )

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.HEADERS)

    def data(self, index: QModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)):
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        row = self._rows[index.row()]
        palette = theme.current_palette()
        if role == int(Qt.ItemDataRole.DisplayRole):
            return {
                0: f"{row.category}  ·  {row.label}",
                1: _format_value(row.value, row.unit),
                2: _format_value(row.minimum, row.unit),
                3: _format_value(row.maximum, row.unit),
                4: (_format_value(row.average, row.unit) if row.samples else "—"),
                5: "Available" if row.value is not None else (row.note or "Unavailable"),
            }.get(index.column(), "")
        if role == int(Qt.ItemDataRole.TextAlignmentRole) and index.column() >= 1 and index.column() <= 4:
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        if role == int(Qt.ItemDataRole.ForegroundRole):
            if index.column() == 5:
                return QColor(palette.success if row.value is not None else palette.warning)
            if index.column() == 1 and row.value is None:
                return QColor(palette.text_muted)
            if index.column() in (2, 3, 4):
                return QColor(palette.text_muted)
        if role == int(Qt.ItemDataRole.ToolTipRole) and index.column() == 5:
            return row.note or ("Measured from a local platform API." if row.value is not None else "Unavailable.")
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = int(Qt.ItemDataRole.DisplayRole)):  # noqa: N802
        if role == int(Qt.ItemDataRole.DisplayRole) and orientation == Qt.Orientation.Horizontal:
            return self.HEADERS[section] if 0 <= section < len(self.HEADERS) else None
        return None


class HardwarePage(BasePage):
    title = "Hardware Monitor"
    subtitle = "Sensors, tracked session statistics and capability status"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._stats: dict[str, RunningStats] = {}
        self._readings: dict[str, SensorReading] = {}
        self._session_started: float | None = None
        self._last_snapshot: Snapshot | None = None
        self._capability_model: RecordsModel | None = None
        self._capabilities_loaded = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = PageScroll()
        root.addWidget(scroll)
        content = scroll.content_layout

        self.availability_card = Card("Sensor availability")
        self.availability_summary = QLabel("Detecting sensors…")
        self.availability_summary.setObjectName("muted")
        self.availability_card.add_header_widget(self.availability_summary)
        self.capability_table = QTableView()
        self.capability_table.setMinimumHeight(150)
        self.availability_card.body.addWidget(self.capability_table)
        content.addWidget(self.availability_card)

        details_row = QHBoxLayout()
        details_row.setSpacing(14)
        self.cpu_card = Card("Processor")
        self.cpu_grid = StatsRow(["Model", "Cores", "Frequency", "Temperature"])
        self.cpu_card.body.addWidget(self.cpu_grid)
        self.gpu_card = Card("Graphics")
        self.gpu_grid = StatsRow(["Adapter", "Driver", "VRAM", "Temperature"])
        self.gpu_card.body.addWidget(self.gpu_grid)
        details_row.addWidget(self.cpu_card, 1)
        details_row.addWidget(self.gpu_card, 1)
        content.addLayout(details_row)

        second_row = QHBoxLayout()
        second_row.setSpacing(14)
        self.memory_card = Card("Memory")
        self.memory_grid = StatsRow(["Installed", "In use", "Available", "Swap" if platform_id() == "macos" else "Page file"])
        self.memory_card.body.addWidget(self.memory_grid)
        self.os_card = Card("Operating system")
        self.os_grid = StatsRow(["Version", "Build", "Architecture", "Uptime"])
        self.os_card.body.addWidget(self.os_grid)
        second_row.addWidget(self.memory_card, 1)
        second_row.addWidget(self.os_card, 1)
        content.addLayout(second_row)

        # Sensors --------------------------------------------------------------
        sensors = Card("Live sensors")
        header = SectionHeader(
            "Sensor readings",
            "Minimum, maximum and average are tracked for this monitoring session.",
        )
        self.session_label = QLabel("Session not started")
        self.session_label.setObjectName("faint")
        header.add_action(self.session_label)
        reset_button = QPushButton("Reset statistics")
        reset_button.setObjectName("ghost")
        reset_button.clicked.connect(self._reset_statistics)
        header.add_action(reset_button)
        sensors.body.addWidget(header)
        self.sensor_model = SensorTableModel(self)
        self.sensor_table = QTableView()
        self.sensor_table.setModel(self.sensor_model)
        self.sensor_table.setShowGrid(False)
        self.sensor_table.setAlternatingRowColors(True)
        self.sensor_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.sensor_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.sensor_table.verticalHeader().setVisible(False)
        self.sensor_table.verticalHeader().setDefaultSectionSize(30)
        self.sensor_table.horizontalHeader().setStretchLastSection(True)
        self.sensor_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.sensor_table.setColumnWidth(0, 250)
        self.sensor_table.setColumnWidth(1, 110)
        self.sensor_table.setColumnWidth(2, 100)
        self.sensor_table.setColumnWidth(3, 100)
        self.sensor_table.setColumnWidth(4, 100)
        self.sensor_table.setMinimumHeight(330)
        sensors.body.addWidget(self.sensor_table)
        content.addWidget(sensors)

        # Storage --------------------------------------------------------------
        storage_row = QHBoxLayout()
        storage_row.setSpacing(14)
        self.volumes_card = Card("Storage volumes")
        self.volumes_model = RecordsModel(
            [
                Column("Volume", lambda p: p.mountpoint, width=90),
                Column("Filesystem", lambda p: p.filesystem, width=90),
                Column("Capacity", lambda p: p.total_bytes, formatter=formatting.format_bytes),
                Column("Free", lambda p: p.free_bytes, formatter=formatting.format_bytes),
                Column(
                    "Used",
                    lambda p: p.percent_used,
                    formatter=lambda v: f"{v:.1f}%",
                    align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                ),
            ]
        )
        self.volumes_table = QTableView()
        configure_table(self.volumes_table, self.volumes_model)
        self.volumes_table.setMinimumHeight(120)
        self.volumes_card.body.addWidget(self.volumes_table)
        storage_row.addWidget(self.volumes_card, 1)

        self.adapters_card = Card("Network adapters")
        self.adapters_model = RecordsModel(
            [
                Column("Adapter", lambda a: a.name, width=150),
                Column("State", lambda a: "Up" if a.is_up else "Down"),
                Column("Download", lambda a: a.received_bytes_per_sec, formatter=formatting.format_rate),
                Column("Upload", lambda a: a.sent_bytes_per_sec, formatter=formatting.format_rate),
                Column(
                    "Link",
                    lambda a: a.link_speed_mbps,
                    formatter=lambda v: f"{v:.0f} Mbit/s" if v else "—",
                ),
            ]
        )
        self.adapters_table = QTableView()
        configure_table(self.adapters_table, self.adapters_model)
        self.adapters_table.setMinimumHeight(150)
        self.adapters_card.body.addWidget(self.adapters_table)
        storage_row.addWidget(self.adapters_card, 1)
        content.addLayout(storage_row)
        content.addStretch(1)

        self.context.monitoring.capabilitiesReady.connect(self._load_capabilities)
        latest = context.monitoring.latest
        if latest is not None:
            self.on_snapshot(latest)
        if context.monitoring.capabilities:
            self._load_capabilities(context.monitoring.capabilities)

    # -- capability table ---------------------------------------------------
    def _load_capabilities(self, capabilities: list[Capability]) -> None:
        model = RecordsModel(
            [
                Column("Sensor", lambda c: c.label, width=210),
                Column(
                    "Availability",
                    lambda c: c.status_text,
                    color=lambda c: theme.current_palette().success if c.available else theme.current_palette().warning,
                    width=110,
                ),
                Column("Detail", lambda c: c.detail or "—"),
            ]
        )
        model.set_records(capabilities)
        self.capability_table.setModel(model)
        self.capability_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.capability_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.capability_table.verticalHeader().setVisible(False)
        self.capability_table.verticalHeader().setDefaultSectionSize(28)
        self.capability_table.horizontalHeader().setStretchLastSection(True)
        self.capability_table.setColumnWidth(0, 210)
        self.capability_table.setColumnWidth(1, 110)
        self._capability_model = model
        available = sum(1 for c in capabilities if c.available)
        self.availability_summary.setText(
            f"{available} of {len(capabilities)} sensor groups available"
        )
        self._capabilities_loaded = True

    # -- lifecycle ----------------------------------------------------------
    def on_activated(self) -> None:
        self.context.processes.set_active(False)
        latest = self.context.monitoring.latest
        if latest is not None:
            self.on_snapshot(latest)

    def refresh_now(self) -> None:
        self.context.monitoring.refresh_now()

    def refresh_theme(self) -> None:
        latest = self._last_snapshot
        if latest is not None:
            self.on_snapshot(latest)
        if self.context.monitoring.capabilities:
            self._load_capabilities(self.context.monitoring.capabilities)

    def _reset_statistics(self) -> None:
        self._stats.clear()
        self._session_started = None
        self.session_label.setText("Statistics reset")
        latest = self._last_snapshot
        if latest is not None:
            self.on_snapshot(latest)

    # -- updates ------------------------------------------------------------
    def on_snapshot(self, snapshot: Snapshot) -> None:
        self._last_snapshot = snapshot
        if self._session_started is None:
            self._session_started = snapshot.timestamp
        self._update_static(snapshot)
        readings = snapshot_readings(snapshot)
        self._readings = {reading.key: reading for reading in readings}
        rows: list[SensorRow] = []
        for reading in readings:
            stats = self._stats.setdefault(reading.key, RunningStats())
            stats.add(reading.value)
            rows.append(
                SensorRow(
                    key=reading.key,
                    category=reading.category,
                    label=reading.label,
                    unit=reading.unit,
                    value=reading.value,
                    minimum=stats.minimum,
                    maximum=stats.maximum,
                    average=stats.average,
                    samples=stats.count,
                    note=reading.note,
                )
            )
        self.sensor_model.update_rows(rows)
        samples = max((row.samples for row in rows), default=0)
        elapsed = int(max(0, snapshot.timestamp - (self._session_started or snapshot.timestamp)))
        self.session_label.setText(
            f"Session {formatting.format_duration(elapsed)} · {samples} samples per sensor"
        )

    def _update_static(self, snapshot: Snapshot) -> None:
        cpu = snapshot.cpu
        if cpu is not None:
            self.cpu_grid.set_values(
                {
                    "Model": cpu.model,
                    "Cores": f"{cpu.physical_cores or '—'} physical · {cpu.logical_cores or '—'} logical",
                    "Frequency": formatting.format_frequency(cpu.frequency_mhz),
                    "Temperature": formatting.format_temperature(cpu.temperature_c),
                }
            )
        gpu = snapshot.gpus[0] if snapshot.gpus else None
        if gpu is not None:
            self.gpu_grid.set_values(
                {
                    "Adapter": gpu.name,
                    "Driver": gpu.driver_version or "Unknown",
                    "VRAM": (
                        f"{formatting.format_bytes(gpu.memory_used_bytes)} / "
                        f"{formatting.format_bytes(gpu.memory_total_bytes)}"
                        if gpu.memory_total_bytes
                        else "Unavailable"
                    ),
                    "Temperature": formatting.format_temperature(gpu.temperature_c),
                }
            )
        else:
            self.gpu_grid.set_values(
                {
                    "Adapter": "Not available through supported macOS interface" if platform_id() == "macos" else "No NVML GPU detected",
                    "Driver": "Unavailable",
                    "VRAM": "Unavailable",
                    "Temperature": "Unavailable",
                }
            )
        memory = snapshot.memory
        if memory is not None:
            page_file = (
                f"{formatting.format_bytes(memory.swap_used_bytes)} / {formatting.format_bytes(memory.swap_total_bytes)}"
                if memory.swap_total_bytes
                else "Unavailable"
            )
            self.memory_grid.set_values(
                {
                    "Installed": formatting.format_bytes(memory.total_bytes) + (" (unified)" if platform_id() == "macos" and architecture_id() == "arm64" else ""),
                    "In use": formatting.format_bytes(memory.used_bytes),
                    "Available": formatting.format_bytes(memory.available_bytes),
                    ("Swap" if platform_id() == "macos" else "Page file"): page_file,
                }
            )
        info = snapshot.system
        if info is not None:
            self.os_grid.set_values(
                {
                    "Version": info.os_version or info.os_name,
                    "Build": info.os_build or "—",
                    "Architecture": info.architecture or "—",
                    "Uptime": formatting.format_duration(info.uptime_seconds),
                }
            )
        if snapshot.disk is not None:
            self.volumes_model.set_records(list(snapshot.disk.partitions))
        if snapshot.network is not None:
            self.adapters_model.set_records(list(snapshot.network.adapters))
