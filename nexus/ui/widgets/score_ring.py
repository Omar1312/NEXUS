"""Painted score ring with a smooth value animation."""

from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF, Qt
from PySide6.QtGui import QColor, QConicalGradient, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from nexus.ui import theme


class ScoreRing(QWidget):
    def __init__(self, parent: QWidget | None = None, *, diameter: int = 168) -> None:
        super().__init__(parent)
        self._value = 0.0
        self._target = 0.0
        self._grade = "—"
        self._caption = ""
        self._available = True
        self.setMinimumSize(diameter, diameter)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._animation = QPropertyAnimation(self, b"value", self)
        self._animation.setDuration(620)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    # -- properties ---------------------------------------------------------
    def _get_value(self) -> float:
        return self._value

    def _set_value(self, value: float) -> None:
        self._value = float(value)
        self.update()

    value = Property(float, _get_value, _set_value)

    def set_score(self, score: int | None, grade: str, caption: str = "", *, animate: bool = True) -> None:
        self._available = score is not None and score > 0
        self._grade = grade
        self._caption = caption
        target = float(score or 0)
        self._target = target
        if animate and self.isVisible():
            self._animation.stop()
            self._animation.setStartValue(self._value)
            self._animation.setEndValue(target)
            self._animation.start()
        else:
            self._value = target
            self.update()

    # -- painting -----------------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: N802
        palette = theme.current_palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        side = min(self.width(), self.height())
        margin = 10.0
        rect = QRectF((self.width() - side) / 2 + margin, (self.height() - side) / 2 + margin, side - 2 * margin, side - 2 * margin)
        thickness = max(8.0, side * 0.062)
        track = QPen(QColor(palette.card_alt), thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(track)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(rect, 0, 360 * 16)

        if self._available:
            if self._value >= 85:
                color = QColor(palette.success)
            elif self._value >= 70:
                color = QColor(palette.accent)
            elif self._value >= 50:
                color = QColor(palette.warning)
            else:
                color = QColor(palette.critical)
            gradient = QConicalGradient(rect.center(), 90)
            lighter = QColor(color)
            lighter.setAlpha(160)
            gradient.setColorAt(0.0, color)
            gradient.setColorAt(0.75, color)
            gradient.setColorAt(1.0, lighter)
            pen = QPen(gradient, thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            span = max(0.0, min(1.0, self._value / 100.0)) * 360.0
            painter.drawArc(rect, 90 * 16, -int(span * 16))

        # Value text
        value_font = QFont()
        value_font.setPointSizeF(max(18.0, side * 0.19))
        value_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(value_font)
        painter.setPen(QColor(palette.text if self._available else palette.text_faint))
        value_text = f"{round(self._value)}" if self._available else "—"
        value_rect = QRectF(rect.left(), rect.top() + side * 0.20, rect.width(), side * 0.34)
        painter.drawText(value_rect, Qt.AlignmentFlag.AlignCenter, value_text)

        suffix_font = QFont()
        suffix_font.setPointSizeF(max(7.5, side * 0.055))
        painter.setFont(suffix_font)
        painter.setPen(QColor(palette.text_muted))
        painter.drawText(
            QRectF(rect.left(), rect.top() + side * 0.50, rect.width(), 16),
            Qt.AlignmentFlag.AlignCenter,
            "out of 100" if self._available else "No data",
        )

        grade_font = QFont()
        grade_font.setPointSizeF(max(8.5, side * 0.064))
        grade_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(grade_font)
        painter.setPen(QColor(palette.text))
        painter.drawText(
            QRectF(rect.left(), rect.top() + side * 0.62, rect.width(), 20),
            Qt.AlignmentFlag.AlignCenter,
            self._grade,
        )
        painter.end()
