"""Charts: smooth bounded time-series, donut and bar visualisations."""

from __future__ import annotations

import math
from collections import deque
from typing import Callable, Sequence

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from nexus.ui import theme
from nexus.utils import formatting


def _axis_pen(palette: theme.Palette) -> QPen:
    pen = QPen(QColor(palette.border_strong))
    pen.setWidthF(1.0)
    return pen


class UnitAxis(pg.AxisItem):
    def __init__(self, formatter: Callable[[float], str], **kwargs) -> None:
        super().__init__(orientation="left", **kwargs)
        self._formatter = formatter
        self.setWidth(52)

    def tickStrings(self, values, scale, spacing):  # noqa: N802 - pyqtgraph API
        return [self._formatter(value) for value in values]


class TimeSeriesChart(QWidget):
    """A dark, grid-light chart with a bounded deque per series."""

    def __init__(
        self,
        series: Sequence[tuple[str, str]],
        *,
        max_points: int = 180,
        y_max: float | None = 100.0,
        height: int = 116,
        formatter: Callable[[float], str] | None = None,
        fill: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._series: list[tuple[str, str]] = list(series)
        self._max_points = max(2, int(max_points))
        self._y_max = y_max
        self._formatter = formatter or (lambda value: f"{value:.0f}")
        self._fill = fill
        self._x: deque[float] = deque(maxlen=self._max_points)
        self._buffers: dict[str, deque[float | None]] = {
            name: deque(maxlen=self._max_points) for name, _ in self._series
        }
        palette = theme.current_palette()
        self._palette = palette

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.plot_widget = pg.PlotWidget(
            axisItems={
                "bottom": pg.DateAxisItem(orientation="bottom"),
                "left": UnitAxis(self._formatter),
            }
        )
        self.plot_widget.setBackground(None)
        self.plot_widget.setMinimumHeight(height)
        self.plot_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.plot_widget)

        plot = self.plot_widget.getPlotItem()
        plot.setMenuEnabled(False)
        plot.hideButtons()
        plot.setMouseEnabled(x=False, y=False)
        plot.setClipToView(True)
        plot.getViewBox().setDefaultPadding(0.06)
        plot.layout.setContentsMargins(0, 2, 4, 0)
        plot.showAxis("top", False)
        plot.showAxis("right", False)
        plot.showGrid(x=False, y=True, alpha=0.15)
        tick_font = QFont()
        tick_font.setPointSizeF(7.0)
        plot.getAxis("bottom").setStyle(tickFont=tick_font, tickLength=3)
        plot.getAxis("left").setStyle(tickFont=tick_font, tickLength=3)
        for axis_name in ("bottom", "left"):
            axis = plot.getAxis(axis_name)
            axis.setPen(_axis_pen(palette))
            axis.setTextPen(QColor(palette.text_faint))
            axis.setLabel("")
        if self._y_max is not None:
            plot.setYRange(0, self._y_max, padding=0)
            plot.setLimits(yMin=0, yMax=self._y_max * 1.2)
        else:
            plot.enableAutoRange(axis="y", enable=True)
            plot.setLimits(yMin=0)

        self._curves: dict[str, pg.PlotDataItem] = {}
        self._legend = None
        if len(self._series) > 1:
            self._legend = plot.addLegend(offset=(0, 0), brush=pg.mkBrush(0, 0, 0, 0))
            self._legend.setLabelTextColor(QColor(palette.text_muted))

        for name, color in self._series:
            pen = pg.mkPen(color=color, width=1.8)
            curve = pg.PlotDataItem(pen=pen)
            if self._fill and len(self._series) == 1:
                fill_color = QColor(color)
                fill_color.setAlpha(34)
                curve.setFillLevel(0)
                curve.setBrush(pg.mkBrush(fill_color))
            plot.addItem(curve)
            if self._legend is not None:
                self._legend.addItem(curve, name)
            self._curves[name] = curve

    # -- data ---------------------------------------------------------------
    def append(self, timestamp: float, values: dict[str, float | None]) -> None:
        self._x.append(float(timestamp))
        for name, _ in self._series:
            value = values.get(name)
            self._buffers[name].append(
                float(value) if value is not None and math.isfinite(float(value)) else None
            )
        self._redraw()

    def set_values(self, points: Sequence[tuple[float, dict[str, float | None]]]) -> None:
        self.clear()
        x = [p[0] for p in points][-self._max_points :]
        self._x.extend(x)
        for name, _ in self._series:
            self._buffers[name].extend(
                [
                    (point[1].get(name) if point[1].get(name) is not None else None)
                    for point in points[-self._max_points :]
                ]
            )
        self._redraw()

    def clear(self) -> None:
        self._x.clear()
        for buffer in self._buffers.values():
            buffer.clear()
        for curve in self._curves.values():
            curve.setData([], [])
        if self._y_max is not None:
            self.plot_widget.getPlotItem().setYRange(0, self._y_max, padding=0)

    def set_max_points(self, points: int) -> None:
        points = max(10, int(points))
        if points == self._max_points:
            return
        self._max_points = points
        x_values = list(self._x)[-points:]
        self._x = deque(x_values, maxlen=points)
        for name, values in list(self._buffers.items()):
            self._buffers[name] = deque(list(values)[-points:], maxlen=points)
        self._redraw()

    def _redraw(self) -> None:
        if not self._x:
            return
        x_array = np.asarray(self._x, dtype=float)
        plot = self.plot_widget.getPlotItem()
        peak = 0.0
        for name, _ in self._series:
            raw = list(self._buffers[name])
            y_array = np.asarray(
                [float(v) if v is not None else np.nan for v in raw], dtype=float
            )
            finite = y_array[np.isfinite(y_array)]
            if finite.size:
                peak = max(peak, float(np.max(finite)))
            self._curves[name].setData(x_array, y_array)
        if self._y_max is None:
            plot.setYRange(0, max(1.0, peak * 1.18), padding=0)

    # -- theme --------------------------------------------------------------
    def apply_theme(self) -> None:
        palette = theme.current_palette()
        self._palette = palette
        plot = self.plot_widget.getPlotItem()
        plot.showGrid(x=False, y=True, alpha=0.15)
        for axis_name in ("bottom", "left"):
            axis = plot.getAxis(axis_name)
            axis.setPen(_axis_pen(palette))
            axis.setTextPen(QColor(palette.text_faint))
        if self._legend is not None:
            self._legend.setLabelTextColor(QColor(palette.text_muted))


class CoreBars(QWidget):
    """Compact per-logical-processor utilization bars."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._values: tuple[float, ...] = ()
        self.setMinimumHeight(58)
        self.setMouseTracking(True)
        self.setToolTip("Per-logical-processor utilization")

    def set_values(self, values: Sequence[float]) -> None:
        clipped = tuple(max(0.0, min(100.0, float(v))) for v in values)
        if clipped != self._values:
            self._values = clipped
            self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        if not self._values:
            return
        palette = theme.current_palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        count = len(self._values)
        columns = min(14, max(4, math.ceil(math.sqrt(count * 1.8))))
        rows = math.ceil(count / columns)
        gap = 3.0
        width = (self.width() - gap * (columns - 1)) / columns
        height = (self.height() - gap * (rows - 1)) / rows
        for index, value in enumerate(self._values):
            row, column = divmod(index, columns)
            x = column * (width + gap)
            y = row * (height + gap)
            background = QColor(palette.card_alt)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(background)
            painter.drawRoundedRect(QRectF(x, y, width, height), 2.0, 2.0)
            if value <= 0:
                continue
            if value >= 90:
                color = QColor(palette.critical)
            elif value >= 65:
                color = QColor(palette.warning)
            else:
                color = QColor(palette.accent)
            fill_height = max(2.0, height * value / 100.0)
            painter.setBrush(color)
            painter.drawRoundedRect(
                QRectF(x, y + height - fill_height, width, fill_height), 2.0, 2.0
            )
        painter.end()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if not self._values:
            return
        count = len(self._values)
        columns = min(14, max(4, math.ceil(math.sqrt(count * 1.8))))
        rows = math.ceil(count / columns)
        gap = 3.0
        width = (self.width() - gap * (columns - 1)) / columns
        height = (self.height() - gap * (rows - 1)) / rows
        column = int(event.position().x() // (width + gap))
        row = int(event.position().y() // (height + gap))
        index = row * columns + column
        if 0 <= index < count and column < columns:
            self.setToolTip(f"Logical processor {index}: {self._values[index]:.0f}%")
        else:
            self.setToolTip("Per-logical-processor utilization")


class PieChart(QWidget):
    """Donut chart with a compact legend; used for file-type distribution."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._data: list[tuple[str, int, str]] = []
        self.setMinimumHeight(190)

    def set_data(self, data: Sequence[tuple[str, int, str]]) -> None:
        self._data = [(label, int(value), color) for label, value, color in data if value > 0]
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        palette = theme.current_palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if not self._data:
            painter.setPen(QColor(palette.text_faint))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No scan data yet")
            painter.end()
            return
        total = sum(value for _, value, _ in self._data)
        size = min(self.height() - 16, self.width() * 0.46)
        rect = QRectF(8, (self.height() - size) / 2, size, size)
        start_angle = 90 * 16
        for _label, value, color in self._data:
            span = -int(360 * 16 * value / total)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(color))
            painter.drawPie(rect, start_angle, span)
            start_angle += span
        hole = rect.adjusted(size * 0.22, size * 0.22, -size * 0.22, -size * 0.22)
        painter.setBrush(QColor(palette.card))
        painter.drawEllipse(hole)
        painter.setPen(QColor(palette.text))
        font = QFont()
        font.setPointSizeF(9.5)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, formatting.format_bytes(total))

        legend_x = size + 30
        legend_width = max(40, self.width() - legend_x - 8)
        line_height = min(24, (self.height() - 20) / max(1, len(self._data)))
        font.setPointSizeF(8.2)
        font.setWeight(QFont.Weight.Normal)
        painter.setFont(font)
        for index, (label, value, color) in enumerate(self._data[:8]):
            y = 14 + index * line_height
            painter.setBrush(QColor(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(legend_x, y + 3, 8, 8), 2, 2)
            painter.setPen(QColor(palette.text_muted))
            text = f"{label}"
            painter.drawText(QRectF(legend_x + 14, y, legend_width - 14, line_height), Qt.AlignmentFlag.AlignVCenter, text)
            painter.setPen(QColor(palette.text_faint))
            painter.drawText(
                QRectF(legend_x + 14, y, legend_width - 14, line_height),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                formatting.format_bytes(value),
            )
        painter.end()


class HBarChart(QWidget):
    """Horizontal bar list for largest directories/categories."""

    def __init__(self, parent: QWidget | None = None, *, rows: int = 8) -> None:
        super().__init__(parent)
        self._items: list[tuple[str, float]] = []
        self._rows = rows
        self.setMinimumHeight(rows * 28 + 8)
        self._formatter = formatting.format_bytes

    def set_formatter(self, formatter: Callable[[float], str]) -> None:
        self._formatter = formatter

    def set_data(self, items: Sequence[tuple[str, float]]) -> None:
        self._items = list(items)[: self._rows]
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        palette = theme.current_palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if not self._items:
            painter.setPen(QColor(palette.text_faint))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No data to display")
            painter.end()
            return
        peak = max((value for _, value in self._items), default=1.0) or 1.0
        label_font = QFont()
        label_font.setPointSizeF(8.4)
        painter.setFont(label_font)
        row_height = (self.height() - 6) / max(1, len(self._items))
        for index, (label, value) in enumerate(self._items):
            y = index * row_height + 3
            text = _elide(label, 46)
            painter.setPen(QColor(palette.text_muted))
            painter.drawText(QRectF(0, y, self.width(), 14), Qt.AlignmentFlag.AlignVCenter, text)
            painter.setPen(QColor(palette.text_faint))
            painter.drawText(
                QRectF(0, y, self.width(), 14),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                self._formatter(value),
            )
            bar_y = y + 15
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(palette.card_alt))
            painter.drawRoundedRect(QRectF(0, bar_y, self.width(), 4), 2, 2)
            painter.setBrush(QColor(palette.accent))
            painter.drawRoundedRect(
                QRectF(0, bar_y, max(3.0, self.width() * value / peak), 4), 2, 2
            )
        painter.end()


class UsageBar(QWidget):
    """Thin segmented capacity bar (used / free)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._percent = 0.0
        self.setFixedHeight(6)

    def set_percent(self, percent: float | None) -> None:
        self._percent = 0.0 if percent is None else max(0.0, min(100.0, percent))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        palette = theme.current_palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(palette.card_alt))
        painter.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), 3, 3)
        color = palette.accent
        if self._percent >= 92:
            color = palette.critical
        elif self._percent >= 80:
            color = palette.warning
        painter.setBrush(QColor(color))
        width = max(0.0, self.width() * self._percent / 100.0)
        if width > 0:
            painter.drawRoundedRect(QRectF(0, 0, width, self.height()), 3, 3)
        painter.end()


def _elide(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"
