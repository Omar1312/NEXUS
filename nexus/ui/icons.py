"""Vector icons drawn at runtime with QPainter.

Keeping icons as code avoids binary assets, guarantees crisp high-DPI
rendering, and lets every icon inherit the active theme colour.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)

_ICON_CACHE: dict[tuple[str, str, int], QIcon] = {}
_PIXMAP_CACHE: dict[tuple[str, str, int], QPixmap] = {}


def _draw(name: str, painter: QPainter) -> None:  # noqa: C901 - icon dispatch
    draw = _DRAWERS.get(name, _draw_info)
    draw(painter)


def _pen(painter: QPainter, color: QColor, width: float = 1.6) -> QPen:
    pen = QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    return pen


def _draw_dashboard(p: QPainter) -> None:
    for x, y, w, h in ((3.5, 3.5, 7, 7), (13.5, 3.5, 7, 4.5), (3.5, 13.5, 7, 7), (13.5, 10.5, 7, 10)):
        p.drawRoundedRect(QRectF(x, y, w, h), 1.6, 1.6)


def _draw_cpu(p: QPainter) -> None:
    p.drawRoundedRect(QRectF(5.5, 5.5, 13, 13), 2, 2)
    p.drawRoundedRect(QRectF(9.5, 9.5, 5, 5), 1, 1)
    for offset in (8, 12, 16):
        p.drawLine(QPointF(offset, 2), QPointF(offset, 5.5))
        p.drawLine(QPointF(offset, 18.5), QPointF(offset, 22))
        p.drawLine(QPointF(2, offset), QPointF(5.5, offset))
        p.drawLine(QPointF(18.5, offset), QPointF(22, offset))


def _draw_gpu(p: QPainter) -> None:
    p.drawRoundedRect(QRectF(2.5, 7, 19, 10), 2, 2)
    p.drawEllipse(QPointF(13.5, 12), 3.2, 3.2)
    p.drawLine(QPointF(5, 17), QPointF(5, 20.5))
    p.drawLine(QPointF(5, 7), QPointF(5, 3.5))


def _draw_processes(p: QPainter) -> None:
    for index, y in enumerate((6.5, 12, 17.5)):
        p.drawEllipse(QPointF(4.6, y), 1.1, 1.1)
        p.drawLine(QPointF(8, y), QPointF(20, y - (0.6 if index == 1 else 0)))


def _draw_optimize(p: QPainter) -> None:
    p.drawArc(QRectF(3.5, 5.5, 17, 17), 30 * 16, 120 * 16)
    p.drawLine(QPointF(12, 14), QPointF(16.2, 9.2))
    p.drawEllipse(QPointF(12, 14), 1.3, 1.3)
    p.drawLine(QPointF(4.5, 19.5), QPointF(7.5, 19.5))


def _draw_startup(p: QPainter) -> None:
    path = QPainterPath()
    path.moveTo(14.5, 4.2)
    path.cubicTo(19.5, 4.0, 20.2, 4.6, 19.8, 9.5)
    path.cubicTo(19.4, 13.0, 15.5, 16.2, 12.0, 17.5)
    path.lineTo(10.5, 15.0)
    path.cubicTo(8.3, 14.2, 5.0, 12.5, 5.3, 12.0)
    path.cubicTo(7.0, 8.5, 11.0, 4.6, 14.5, 4.2)
    p.drawPath(path)
    p.drawEllipse(QPointF(14.6, 9.3), 1.6, 1.6)
    p.drawLine(QPointF(7.2, 16.8), QPointF(4.2, 19.8))
    p.drawLine(QPointF(10.4, 17.6), QPointF(6.4, 19.6))
    p.drawLine(QPointF(6.5, 13.6), QPointF(4.5, 17.6))


def _draw_storage(p: QPainter) -> None:
    p.drawEllipse(QRectF(5, 3.5, 14, 5))
    p.drawLine(QPointF(5, 6), QPointF(5, 18))
    p.drawLine(QPointF(19, 6), QPointF(19, 18))
    p.drawArc(QRectF(5, 15.5, 14, 5), 180 * 16, 180 * 16)
    p.drawArc(QRectF(5, 9.7, 14, 5), 180 * 16, 180 * 16)


def _draw_gaming(p: QPainter) -> None:
    p.drawRoundedRect(QRectF(2.5, 7.5, 19, 10), 4, 4)
    p.drawLine(QPointF(7.5, 11), QPointF(7.5, 14))
    p.drawLine(QPointF(6, 12.5), QPointF(9, 12.5))
    p.drawEllipse(QPointF(16, 11.7), 1.0, 1.0)
    p.drawEllipse(QPointF(18.2, 13.8), 1.0, 1.0)


def _draw_history(p: QPainter) -> None:
    p.drawLine(QPointF(3.5, 20.5), QPointF(20.5, 20.5))
    p.drawLine(QPointF(3.5, 20.5), QPointF(3.5, 3.5))
    path = QPainterPath()
    path.moveTo(6.5, 16.5)
    path.lineTo(10, 12)
    path.lineTo(13, 14.5)
    path.lineTo(18.5, 7)
    p.drawPath(path)


def _draw_reports(p: QPainter) -> None:
    path = QPainterPath()
    path.moveTo(6, 2.8)
    path.lineTo(14, 2.8)
    path.lineTo(19, 7.8)
    path.lineTo(19, 21.2)
    path.lineTo(6, 21.2)
    path.closeSubpath()
    p.drawPath(path)
    p.drawLine(QPointF(14, 2.8), QPointF(14, 7.8))
    p.drawLine(QPointF(14, 7.8), QPointF(19, 7.8))
    for y in (12, 15.2, 18.4):
        p.drawLine(QPointF(9, y), QPointF(16, y))


def _draw_settings(p: QPainter) -> None:
    p.drawEllipse(QPointF(12, 12), 3.2, 3.2)
    for index in range(8):
        angle = index * math.pi / 4
        inner = QPointF(12 + 6.2 * math.cos(angle), 12 + 6.2 * math.sin(angle))
        outer = QPointF(12 + 8.3 * math.cos(angle), 12 + 8.3 * math.sin(angle))
        p.drawLine(inner, outer)
    p.drawEllipse(QPointF(12, 12), 8.2, 8.2)


def _draw_refresh(p: QPainter) -> None:
    p.drawArc(QRectF(4, 4, 16, 16), 40 * 16, 285 * 16)
    path = QPainterPath()
    path.moveTo(18.2, 3.6)
    path.lineTo(19.6, 8.6)
    path.lineTo(14.7, 7.4)
    p.drawPath(path)


def _draw_pause(p: QPainter) -> None:
    p.drawRoundedRect(QRectF(7, 5, 3.4, 14), 1, 1)
    p.drawRoundedRect(QRectF(13.6, 5, 3.4, 14), 1, 1)


def _draw_play(p: QPainter) -> None:
    path = QPainterPath()
    path.moveTo(7.5, 4.8)
    path.lineTo(19.5, 12)
    path.lineTo(7.5, 19.2)
    path.closeSubpath()
    p.drawPath(path)


def _draw_sun(p: QPainter) -> None:
    p.drawEllipse(QPointF(12, 12), 4.2, 4.2)
    for index in range(8):
        angle = index * math.pi / 4
        p.drawLine(
            QPointF(12 + 6.6 * math.cos(angle), 12 + 6.6 * math.sin(angle)),
            QPointF(12 + 8.8 * math.cos(angle), 12 + 8.8 * math.sin(angle)),
        )


def _draw_moon(p: QPainter) -> None:
    path = QPainterPath()
    path.moveTo(15.5, 3.8)
    path.cubicTo(8.6, 5.5, 7.2, 15.8, 15.2, 20.0)
    path.cubicTo(11.2, 20.8, 6.0, 18.2, 5.2, 12.4)
    path.cubicTo(4.4, 6.8, 9.2, 3.0, 15.5, 3.8)
    p.drawPath(path)


def _draw_search(p: QPainter) -> None:
    p.drawEllipse(QPointF(10.5, 10.5), 6.2, 6.2)
    p.drawLine(QPointF(15.2, 15.2), QPointF(20.5, 20.5))


def _draw_folder(p: QPainter) -> None:
    path = QPainterPath()
    path.moveTo(3, 6)
    path.lineTo(9.5, 6)
    path.lineTo(11.5, 8.5)
    path.lineTo(21, 8.5)
    path.lineTo(21, 19)
    path.lineTo(3, 19)
    path.closeSubpath()
    p.drawPath(path)


def _draw_trash(p: QPainter) -> None:
    p.drawLine(QPointF(4, 6.5), QPointF(20, 6.5))
    p.drawLine(QPointF(9, 3.8), QPointF(15, 3.8))
    path = QPainterPath()
    path.moveTo(6, 6.5)
    path.lineTo(7.3, 20.5)
    path.lineTo(16.7, 20.5)
    path.lineTo(18, 6.5)
    p.drawPath(path)
    p.drawLine(QPointF(10.2, 10), QPointF(10.6, 17))
    p.drawLine(QPointF(13.8, 10), QPointF(13.4, 17))


def _draw_export(p: QPainter) -> None:
    p.drawLine(QPointF(12, 3.5), QPointF(12, 14.5))
    path = QPainterPath()
    path.moveTo(7.6, 10.2)
    path.lineTo(12, 14.6)
    path.lineTo(16.4, 10.2)
    p.drawPath(path)
    path = QPainterPath()
    path.moveTo(4, 16)
    path.lineTo(4, 20)
    path.lineTo(20, 20)
    path.lineTo(20, 16)
    p.drawPath(path)


def _draw_external(p: QPainter) -> None:
    p.drawRoundedRect(QRectF(4, 8, 12, 12), 2, 2)
    p.drawLine(QPointF(13, 4), QPointF(20, 4))
    p.drawLine(QPointF(20, 4), QPointF(20, 11))
    p.drawLine(QPointF(20, 4), QPointF(11.5, 12.5))


def _draw_info(p: QPainter) -> None:
    p.drawEllipse(QPointF(12, 12), 8.5, 8.5)
    p.drawLine(QPointF(12, 11), QPointF(12, 16.5))
    p.drawEllipse(QPointF(12, 7.8), 0.9, 0.9)


def _draw_warning(p: QPainter) -> None:
    path = QPainterPath()
    path.moveTo(12, 3.8)
    path.lineTo(21.2, 20)
    path.lineTo(2.8, 20)
    path.closeSubpath()
    p.drawPath(path)
    p.drawLine(QPointF(12, 9.2), QPointF(12, 14.2))
    p.drawEllipse(QPointF(12, 17.2), 0.9, 0.9)


def _draw_shield(p: QPainter) -> None:
    path = QPainterPath()
    path.moveTo(12, 2.8)
    path.lineTo(19.5, 5.8)
    path.lineTo(19.5, 11.5)
    path.cubicTo(19.5, 16.5, 16.2, 19.8, 12, 21.4)
    path.cubicTo(7.8, 19.8, 4.5, 16.5, 4.5, 11.5)
    path.lineTo(4.5, 5.8)
    path.closeSubpath()
    p.drawPath(path)
    path = QPainterPath()
    path.moveTo(8.2, 12)
    path.lineTo(11.1, 14.9)
    path.lineTo(15.9, 9.2)
    p.drawPath(path)


def _draw_clock(p: QPainter) -> None:
    p.drawEllipse(QPointF(12, 12), 8.5, 8.5)
    p.drawLine(QPointF(12, 7), QPointF(12, 12))
    p.drawLine(QPointF(12, 12), QPointF(15.6, 13.8))


def _draw_download(p: QPainter) -> None:
    p.drawLine(QPointF(12, 3.5), QPointF(12, 15))
    path = QPainterPath()
    path.moveTo(7.2, 10.4)
    path.lineTo(12, 15.2)
    path.lineTo(16.8, 10.4)
    p.drawPath(path)
    p.drawLine(QPointF(4, 20.2), QPointF(20, 20.2))


def _draw_ram(p: QPainter) -> None:
    p.drawRoundedRect(QRectF(2.8, 6.5, 18.4, 9), 1.8, 1.8)
    for x in (7.0, 10.2, 13.4, 16.6):
        p.drawLine(QPointF(x, 9), QPointF(x, 13))
    for x in (5, 9.5, 14.5, 19):
        p.drawLine(QPointF(x, 15.5), QPointF(x, 18.5))


def _draw_network(p: QPainter) -> None:
    p.drawEllipse(QPointF(12, 5), 2.2, 2.2)
    p.drawEllipse(QPointF(5.5, 18), 2.2, 2.2)
    p.drawEllipse(QPointF(18.5, 18), 2.2, 2.2)
    p.drawLine(QPointF(10.8, 6.9), QPointF(6.6, 15.8))
    p.drawLine(QPointF(13.2, 6.9), QPointF(17.4, 15.8))
    p.drawLine(QPointF(7.7, 18), QPointF(16.3, 18))


def _draw_check(p: QPainter) -> None:
    path = QPainterPath()
    path.moveTo(4.5, 12.5)
    path.lineTo(9.5, 17.5)
    path.lineTo(19.5, 6.5)
    p.drawPath(path)


def _draw_close(p: QPainter) -> None:
    p.drawLine(QPointF(5.5, 5.5), QPointF(18.5, 18.5))
    p.drawLine(QPointF(18.5, 5.5), QPointF(5.5, 18.5))


def _draw_bolt(p: QPainter) -> None:
    path = QPainterPath()
    path.moveTo(13.5, 2.5)
    path.lineTo(5.5, 13.5)
    path.lineTo(11.2, 13.5)
    path.lineTo(10.2, 21.5)
    path.lineTo(18.5, 10.2)
    path.lineTo(12.7, 10.2)
    path.closeSubpath()
    p.drawPath(path)


def _draw_database(p: QPainter) -> None:
    _draw_storage(p)


def _draw_chevron_right(p: QPainter) -> None:
    path = QPainterPath()
    path.moveTo(9, 5)
    path.lineTo(16, 12)
    path.lineTo(9, 19)
    p.drawPath(path)


_DRAWERS = {
    "dashboard": _draw_dashboard,
    "cpu": _draw_cpu,
    "gpu": _draw_gpu,
    "processes": _draw_processes,
    "optimize": _draw_optimize,
    "startup": _draw_startup,
    "storage": _draw_storage,
    "gaming": _draw_gaming,
    "history": _draw_history,
    "reports": _draw_reports,
    "settings": _draw_settings,
    "refresh": _draw_refresh,
    "pause": _draw_pause,
    "play": _draw_play,
    "sun": _draw_sun,
    "moon": _draw_moon,
    "search": _draw_search,
    "folder": _draw_folder,
    "trash": _draw_trash,
    "export": _draw_export,
    "external": _draw_external,
    "info": _draw_info,
    "warning": _draw_warning,
    "shield": _draw_shield,
    "clock": _draw_clock,
    "download": _draw_download,
    "ram": _draw_ram,
    "network": _draw_network,
    "check": _draw_check,
    "close": _draw_close,
    "bolt": _draw_bolt,
    "database": _draw_database,
    "chevron": _draw_chevron_right,
}


def icon_pixmap(name: str, color: str, size: int = 20) -> QPixmap:
    key = (name, color, size)
    if key in _PIXMAP_CACHE:
        return _PIXMAP_CACHE[key]
    scale = 2
    pixmap = QPixmap(size * scale, size * scale)
    pixmap.setDevicePixelRatio(scale)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.scale(size * scale / 24.0, size * scale / 24.0)
    _pen(painter, QColor(color))
    _draw(name, painter)
    painter.end()
    _PIXMAP_CACHE[key] = pixmap
    return pixmap


def make_icon(name: str, color: str, size: int = 20, active_color: str | None = None) -> QIcon:
    key = (name, color + (active_color or ""), size)
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]
    icon = QIcon()
    icon.addPixmap(icon_pixmap(name, color, size), QIcon.Mode.Normal, QIcon.State.Off)
    icon.addPixmap(icon_pixmap(name, active_color or color, size), QIcon.Mode.Selected, QIcon.State.Off)
    icon.addPixmap(
        icon_pixmap(name, active_color or color, size), QIcon.Mode.Normal, QIcon.State.On
    )
    icon.addPixmap(
        icon_pixmap(name, active_color or color, size), QIcon.Mode.Selected, QIcon.State.On
    )
    _ICON_CACHE[key] = icon
    return icon


def logo_pixmap(size: int = 40) -> QPixmap:
    scale = 2
    pixmap = QPixmap(size * scale, size * scale)
    pixmap.setDevicePixelRatio(scale)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.scale(size * scale / 48.0, size * scale / 48.0)
    gradient = QLinearGradient(6, 4, 42, 44)
    gradient.setColorAt(0.0, QColor("#818CF8"))
    gradient.setColorAt(0.55, QColor("#6366F1"))
    gradient.setColorAt(1.0, QColor("#4338CA"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(gradient)
    painter.drawRoundedRect(QRectF(2, 2, 44, 44), 13, 13)
    # Subtle inner highlight
    painter.setBrush(QColor(255, 255, 255, 18))
    painter.drawRoundedRect(QRectF(6, 6, 36, 18), 9, 9)
    font = QFont("Segoe UI", 24)
    font.setWeight(QFont.Weight.Bold)
    painter.setFont(font)
    painter.setPen(QColor("#FFFFFF"))
    painter.drawText(QRectF(2, 1, 44, 44), Qt.AlignmentFlag.AlignCenter, "N")
    painter.end()
    return pixmap


def app_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(logo_pixmap(size))
    return icon
