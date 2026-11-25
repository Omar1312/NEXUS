"""Sidebar navigation with painted logo and themed icons."""

from __future__ import annotations

import sys

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from nexus import __version__
from nexus.ui import icons, theme

_MODIFIER = "Meta" if sys.platform == "darwin" else "Ctrl"
NAV_ITEMS: tuple[tuple[str, str, str, str], ...] = (
    ("dashboard", "Dashboard", "dashboard", f"{_MODIFIER}+1"),
    ("hardware", "Hardware Monitor", "cpu", f"{_MODIFIER}+2"),
    ("processes", "Processes", "processes", f"{_MODIFIER}+3"),
    ("optimizer", "Optimization Center", "optimize", f"{_MODIFIER}+4"),
    ("startup", "Startup Applications", "startup", f"{_MODIFIER}+5"),
    ("storage", "Storage Analyzer", "storage", f"{_MODIFIER}+6"),
    ("gaming", "Gaming Mode", "gaming", f"{_MODIFIER}+7"),
    ("history", "Performance History", "history", f"{_MODIFIER}+8"),
    ("reports", "Reports", "reports", f"{_MODIFIER}+9"),
    ("settings", "Settings", "settings", f"{_MODIFIER}+0"),
)


class Sidebar(QFrame):
    pageSelected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(228)
        self._buttons: dict[str, QToolButton] = {}
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 18, 14, 14)
        layout.setSpacing(4)

        brand = QHBoxLayout()
        brand.setContentsMargins(6, 0, 0, 0)
        brand.setSpacing(10)
        logo = QLabel()
        logo.setPixmap(icons.logo_pixmap(38))
        logo.setFixedSize(38, 38)
        text_box = QVBoxLayout()
        text_box.setSpacing(0)
        name = QLabel("NEXUS")
        name.setObjectName("brandName")
        tagline = QLabel("PERFORMANCE SUITE")
        tagline.setObjectName("brandTagline")
        text_box.addWidget(name)
        text_box.addWidget(tagline)
        brand.addWidget(logo, 0, Qt.AlignmentFlag.AlignVCenter)
        brand.addLayout(text_box, 1)
        layout.addLayout(brand)
        layout.addSpacing(18)

        section = QLabel("OVERVIEW")
        section.setObjectName("faint")
        section.setContentsMargins(10, 0, 0, 2)
        layout.addWidget(section)
        layout.addSpacing(2)

        palette = theme.current_palette()
        for index, (key, label, icon_name, shortcut) in enumerate(NAV_ITEMS):
            if key == "gaming":
                layout.addSpacing(10)
                section = QLabel("TOOLS")
                section.setObjectName("faint")
                section.setContentsMargins(10, 0, 0, 2)
                layout.addWidget(section)
                layout.addSpacing(2)
            button = QToolButton()
            button.setObjectName("navButton")
            button.setText(label)
            button.setCheckable(True)
            button.setAutoRaise(True)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            button.setIconSize(QSize(18, 18))
            button.setIcon(
                icons.make_icon(icon_name, palette.text_muted, 18, palette.accent_hover)
            )
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            button.setFixedHeight(38)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setToolTip(f"{label}  ({shortcut})")
            button.clicked.connect(lambda _checked=False, k=key: self.pageSelected.emit(k))
            self._group.addButton(button, index)
            layout.addWidget(button)
            self._buttons[key] = button

        layout.addStretch(1)

        footer = QFrame()
        footer.setObjectName("innerCard")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(11, 9, 11, 9)
        footer_layout.setSpacing(4)
        privacy = QHBoxLayout()
        privacy.setSpacing(6)
        shield = QLabel()
        shield.setPixmap(icons.icon_pixmap("shield", palette.success, 13))
        shield.setFixedSize(14, 14)
        privacy_text = QLabel("Local-first · no telemetry")
        privacy_text.setObjectName("faint")
        privacy.addWidget(shield)
        privacy.addWidget(privacy_text, 1)
        footer_layout.addLayout(privacy)
        version = QLabel(f"Version {__version__}")
        version.setObjectName("faint")
        footer_layout.addWidget(version)
        layout.addWidget(footer)

    def set_current(self, key: str) -> None:
        button = self._buttons.get(key)
        if button is not None:
            button.setChecked(True)

    def refresh_theme(self) -> None:
        palette = theme.current_palette()
        for (key, _label, icon_name, _shortcut), button in zip(NAV_ITEMS, self._buttons.values()):
            button.setIcon(
                icons.make_icon(icon_name, palette.text_muted, 18, palette.accent_hover)
            )
        # Footer icon
        shield = self.findChild(QLabel)
        if shield is not None:
            pass
