"""Reusable cards, badges and layout helpers."""

from __future__ import annotations

from typing import Iterable

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from nexus.ui import icons, theme

LEVEL_OBJECTS = {
    "success": "badgeSuccess",
    "warning": "badgeWarning",
    "critical": "badgeCritical",
    "info": "badgeInfo",
    "neutral": "badgeNeutral",
}


class Card(QFrame):
    """Rounded surface with an optional title row and a content layout."""

    def __init__(self, title: str = "", *, parent: QWidget | None = None, padding: int = 16) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(padding, padding, padding, padding)
        outer.setSpacing(10)
        self._outer = outer
        self._header: QHBoxLayout | None = None
        self._title_label: QLabel | None = None
        if title:
            self._header = QHBoxLayout()
            self._header.setContentsMargins(0, 0, 0, 0)
            self._header.setSpacing(8)
            self._title_label = QLabel(title.upper())
            self._title_label.setObjectName("cardTitle")
            self._header.addWidget(self._title_label)
            self._header.addStretch(1)
            outer.addLayout(self._header)
        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(8)
        outer.addLayout(self.body, 1)

    @property
    def title_label(self) -> QLabel | None:
        return self._title_label

    def add_header_widget(self, widget: QWidget) -> None:
        if self._header is not None:
            self._header.addWidget(widget)

    def add_action(self, widget: QWidget) -> None:
        self.add_header_widget(widget)


class MetricCard(Card):
    """Headline metric with value, unit, subtitle, progress bar and content area."""

    def __init__(
        self,
        title: str,
        icon_name: str,
        *,
        unit: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title, parent=parent, padding=16)
        self._icon_name = icon_name
        palette = theme.current_palette()
        self._icon_label = QLabel()
        self._icon_label.setPixmap(icons.icon_pixmap(icon_name, palette.accent_hover, 16))
        self._icon_label.setFixedSize(18, 18)
        if self._header is not None:
            self._header.insertWidget(0, self._icon_label)
            self._header.insertSpacing(0, 2)
        self._badge: QLabel | None = None

        value_row = QHBoxLayout()
        value_row.setContentsMargins(0, 0, 0, 0)
        value_row.setSpacing(6)
        self.value_label = QLabel("—")
        self.value_label.setObjectName("cardValue")
        self.unit_label = QLabel(unit)
        self.unit_label.setObjectName("cardUnit")
        value_row.addWidget(self.value_label, 0, Qt.AlignmentFlag.AlignBottom)
        value_row.addWidget(self.unit_label, 0, Qt.AlignmentFlag.AlignBottom)
        value_row.addStretch(1)
        self.body.addLayout(value_row)

        self.subtitle_label = QLabel("Waiting for first sample…")
        self.subtitle_label.setObjectName("cardSubtitle")
        self.subtitle_label.setWordWrap(True)
        self.body.addWidget(self.subtitle_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        self.progress.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.body.addWidget(self.progress)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 2, 0, 0)
        self.content_layout.setSpacing(6)
        self.body.addWidget(self.content, 1)

    def set_value(self, text: str, unit: str | None = None) -> None:
        self.value_label.setText(text)
        if unit is not None:
            self.unit_label.setText(unit)

    def set_subtitle(self, text: str) -> None:
        self.subtitle_label.setText(text)

    def set_progress(self, value: float | None, color: str | None = None) -> None:
        palette = theme.current_palette()
        if value is None:
            self.progress.setValue(0)
            self.progress.setVisible(False)
            return
        self.progress.setVisible(True)
        self.progress.setValue(int(max(0.0, min(100.0, value)) * 10))
        if color:
            self.progress.setStyleSheet(
                f"QProgressBar::chunk {{ background-color: {color}; border-radius: 3px; }}"
            )
        else:
            self.progress.setStyleSheet("")

    def set_badge(self, text: str, level: str = "neutral") -> None:
        if self._badge is None:
            self._badge = QLabel()
            self.add_header_widget(self._badge)
        self._badge.setText(text)
        self._badge.setObjectName(LEVEL_OBJECTS.get(level, "badgeNeutral"))

    def add_content(self, widget: QWidget) -> None:
        self.content_layout.addWidget(widget)

    def refresh_theme(self) -> None:
        palette = theme.current_palette()
        self._icon_label.setPixmap(icons.icon_pixmap(self._icon_name, palette.accent_hover, 16))


class StatTile(QFrame):
    def __init__(self, label: str, value: str = "—", hint: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("innerCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)
        self.label = QLabel(label.upper())
        self.label.setObjectName("metricLabel")
        self.value = QLabel(value)
        self.value.setObjectName("metricValue")
        self.hint = QLabel(hint)
        self.hint.setObjectName("faint")
        self.hint.setWordWrap(True)
        layout.addWidget(self.label)
        layout.addWidget(self.value)
        layout.addWidget(self.hint)

    def set_value(self, value: str, hint: str | None = None) -> None:
        self.value.setText(value)
        if hint is not None:
            self.hint.setText(hint)


class Badge(QLabel):
    def __init__(self, text: str, level: str = "neutral", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.set_level(level)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def set_level(self, level: str) -> None:
        self.setObjectName(LEVEL_OBJECTS.get(level, "badgeNeutral"))
        self.style().unpolish(self)
        self.style().polish(self)


class Banner(QFrame):
    def __init__(
        self,
        text: str,
        *,
        level: str = "warning",
        icon_name: str = "warning",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        palette = theme.current_palette()
        self.setObjectName("warningBanner" if level != "critical" else "dangerBanner")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(10)
        icon = QLabel()
        color = palette.warning if level != "critical" else palette.critical
        icon.setPixmap(icons.icon_pixmap(icon_name, color, 16))
        icon.setFixedSize(18, 18)
        layout.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
        self.text_label = QLabel(text)
        self.text_label.setWordWrap(True)
        self.text_label.setObjectName("muted")
        layout.addWidget(self.text_label, 1)
        self._layout = layout

    def add_action(self, widget: QWidget) -> None:
        self._layout.addWidget(widget)


class SectionHeader(QWidget):
    def __init__(self, title: str, subtitle: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        text_box = QVBoxLayout()
        text_box.setSpacing(1)
        self.title = QLabel(title)
        self.title.setObjectName("sectionTitle")
        self.subtitle = QLabel(subtitle)
        self.subtitle.setObjectName("faint")
        self.subtitle.setVisible(bool(subtitle))
        text_box.addWidget(self.title)
        text_box.addWidget(self.subtitle)
        layout.addLayout(text_box, 1)
        self.actions = QHBoxLayout()
        self.actions.setSpacing(6)
        layout.addLayout(self.actions)

    def add_action(self, widget: QWidget) -> None:
        self.actions.addWidget(widget)


class Divider(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("divider")
        self.setFixedHeight(1)


class KeyValueGrid(QWidget):
    def __init__(self, rows: Iterable[tuple[str, str]] = (), *, columns: int = 2, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(18)
        self._grid.setVerticalSpacing(7)
        self._columns = max(1, columns)
        self._labels: dict[str, QLabel] = {}
        rows = list(rows)
        for index, (key, value) in enumerate(rows):
            self._add(key, value, index)

    def _add(self, key: str, value: str, index: int) -> None:
        row, column = divmod(index, self._columns)
        label = QLabel(key)
        label.setObjectName("muted")
        value_label = QLabel(value)
        value_label.setWordWrap(True)
        value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        holder = QWidget()
        holder_layout = QVBoxLayout(holder)
        holder_layout.setContentsMargins(0, 0, 0, 0)
        holder_layout.setSpacing(1)
        holder_layout.addWidget(label)
        holder_layout.addWidget(value_label)
        self._grid.addWidget(holder, row, column)
        self._labels[key] = value_label

    def set_value(self, key: str, value: str) -> None:
        if key not in self._labels:
            self._add(key, value, len(self._labels))
        self._labels[key].setText(value)

    def set_rows(self, rows: Iterable[tuple[str, str]]) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._labels.clear()
        for index, (key, value) in enumerate(rows):
            self._add(key, value, index)


class EmptyState(QWidget):
    def __init__(self, title: str, description: str, icon_name: str = "info", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        palette = theme.current_palette()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 34, 24, 34)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon = QLabel()
        icon.setPixmap(icons.icon_pixmap(icon_name, palette.text_faint, 34))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 11pt; font-weight: 600;")
        description_label = QLabel(description)
        description_label.setObjectName("muted")
        description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description_label.setWordWrap(True)
        layout.addWidget(icon, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title_label)
        layout.addWidget(description_label)


def hspacer() -> QWidget:
    spacer = QWidget()
    spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    return spacer


def icon_label(name: str, color: str | None = None, size: int = 16) -> QLabel:
    palette = theme.current_palette()
    label = QLabel()
    label.setPixmap(icons.icon_pixmap(name, color or palette.text_muted, size))
    label.setFixedSize(QSize(size + 2, size + 2))
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label


class StatsRow(QWidget):
    """Compact multi-column label/value strip used inside metric cards."""

    def __init__(self, labels: Iterable[str], *, columns: int | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._labels = list(labels)
        self._values: dict[str, QLabel] = {}
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(4)
        cols = columns or min(4, max(1, len(self._labels)))
        for index, label in enumerate(self._labels):
            row, column = divmod(index, cols)
            holder = QWidget()
            box = QVBoxLayout(holder)
            box.setContentsMargins(0, 0, 0, 0)
            box.setSpacing(0)
            key = QLabel(label.upper())
            key.setObjectName("metricLabel")
            value = QLabel("—")
            value.setStyleSheet("font-size: 9.5pt; font-weight: 600;")
            box.addWidget(key)
            box.addWidget(value)
            grid.addWidget(holder, row, column)
            self._values[label] = value

    def set_value(self, label: str, value: str) -> None:
        if label in self._values:
            self._values[label].setText(value)

    def set_values(self, values: dict[str, str]) -> None:
        for label, value in values.items():
            self.set_value(label, value)


class PageScroll(QScrollArea):
    """Scrollable page body with consistent margins and spacing."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        margins: tuple[int, int, int, int] = (22, 16, 22, 20),
        spacing: int = 14,
    ) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget()
        inner.setObjectName("pageRoot")
        self.content_layout = QVBoxLayout(inner)
        self.content_layout.setContentsMargins(*margins)
        self.content_layout.setSpacing(spacing)
        self.setWidget(inner)


class _StatusDot(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = theme.current_palette().success
        self.setFixedSize(10, 10)

    def set_color(self, color: str) -> None:
        self._color = color
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        glow = QColor(self._color)
        glow.setAlpha(70)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(QRectF(0, 0, 10, 10))
        painter.setBrush(QColor(self._color))
        painter.drawEllipse(QRectF(2.5, 2.5, 5, 5))
        painter.end()


class StatusPill(QFrame):
    """Header status chip: coloured dot + text."""

    def __init__(self, text: str = "Starting…", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("statusPill")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 12, 4)
        layout.setSpacing(7)
        self._dot = _StatusDot()
        self._label = QLabel(text)
        self._label.setStyleSheet("font-size: 8.5pt; font-weight: 600;")
        layout.addWidget(self._dot, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._label, 0, Qt.AlignmentFlag.AlignVCenter)

    def set_state(self, text: str, color: str) -> None:
        self._label.setText(text)
        self._dot.set_color(color)

