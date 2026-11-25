"""Visual theme: restrained palette, QSS and system theme resolution."""

from __future__ import annotations

import logging
import sys
from dataclasses import asdict, dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication
from PySide6.QtWidgets import QApplication

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Palette:
    name: str
    background: str
    sidebar: str
    card: str
    card_alt: str
    border: str
    border_strong: str
    accent: str
    accent_hover: str
    accent_soft: str
    success: str
    warning: str
    critical: str
    text: str
    text_muted: str
    text_faint: str
    hover: str
    selection: str
    chart_grid: str
    shadow: str


DARK = Palette(
    name="dark",
    background="#0B0F19",
    sidebar="#111827",
    card="#151D2B",
    card_alt="#1B2435",
    border="#233047",
    border_strong="#31415C",
    accent="#6366F1",
    accent_hover="#818CF8",
    accent_soft="rgba(99, 102, 241, 0.16)",
    success="#22C55E",
    warning="#F59E0B",
    critical="#EF4444",
    text="#F9FAFB",
    text_muted="#9CA3AF",
    text_faint="#6B7280",
    hover="#1B2435",
    selection="rgba(99, 102, 241, 0.22)",
    chart_grid="rgba(156, 163, 175, 0.12)",
    shadow="rgba(0, 0, 0, 0.45)",
)

LIGHT = Palette(
    name="light",
    background="#F4F6FB",
    sidebar="#FFFFFF",
    card="#FFFFFF",
    card_alt="#F1F4F9",
    border="#E2E8F0",
    border_strong="#CBD5E1",
    accent="#4F46E5",
    accent_hover="#6366F1",
    accent_soft="rgba(79, 70, 229, 0.10)",
    success="#16A34A",
    warning="#D97706",
    critical="#DC2626",
    text="#0F172A",
    text_muted="#64748B",
    text_faint="#94A3B8",
    hover="#F1F5F9",
    selection="rgba(79, 70, 229, 0.14)",
    chart_grid="rgba(100, 116, 139, 0.16)",
    shadow="rgba(15, 23, 42, 0.10)",
)

PALETTES = {"dark": DARK, "light": LIGHT}
_current = DARK


def current_palette() -> Palette:
    return _current


def set_current_palette(palette: Palette) -> None:
    global _current
    _current = palette


def candidate_font_family() -> str:
    families = set(QFontDatabase.families())
    for candidate in ("Segoe UI Variable Text", "Segoe UI", "Inter", "Arial"):
        if candidate in families:
            return candidate
    return QFont().family()


def resolve_theme(mode: str) -> str:
    """Resolve the requested system color scheme through native platform hints."""
    if mode in PALETTES:
        return mode
    if sys.platform == "darwin":
        try:
            scheme = QGuiApplication.styleHints().colorScheme()
            if scheme == Qt.ColorScheme.Light:
                return "light"
            if scheme == Qt.ColorScheme.Dark:
                return "dark"
        except (AttributeError, RuntimeError):
            pass
        return "dark"
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
            apps_light, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return "light" if int(apps_light) else "dark"
    except (OSError, ImportError, ValueError, TypeError):
        return "dark"


def apply_theme(app: QApplication, mode: str) -> str:
    """Apply QSS for ``mode`` and return the resolved theme name."""
    resolved = resolve_theme(mode)
    palette = PALETTES[resolved]
    set_current_palette(palette)
    app.setStyleSheet(build_stylesheet(palette))
    font = QFont(candidate_font_family(), 10)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)
    log.info("Theme applied: %s (requested %s)", resolved, mode)
    return resolved


def build_stylesheet(p: Palette) -> str:
    qss = f"""
    * {{
        outline: 0;
        selection-background-color: {p.accent};
        selection-color: #FFFFFF;
    }}
    QWidget {{
        color: {p.text};
        font-family: "Segoe UI Variable Text", "Segoe UI", "Inter", Arial;
        font-size: 10pt;
    }}
    QMainWindow, QDialog, QWidget#appRoot, QWidget#pageRoot {{
        background-color: {p.background};
    }}
    QScrollArea, QScrollArea > QWidget > QWidget {{
        background: transparent;
        border: none;
    }}
    QFrame#sidebar {{
        background-color: {p.sidebar};
        border-right: 1px solid {p.border};
    }}
    QLabel#brandName {{
        font-size: 15pt;
        font-weight: 700;
        letter-spacing: 3px;
        color: {p.text};
    }}
    QLabel#brandTagline {{
        color: {p.text_faint};
        font-size: 7.5pt;
        letter-spacing: 1.5px;
    }}
    QLabel#pageTitle {{
        font-size: 19pt;
        font-weight: 650;
        color: {p.text};
    }}
    QLabel#pageSubtitle {{
        color: {p.text_muted};
        font-size: 9.5pt;
    }}
    QLabel#cardTitle {{
        color: {p.text_muted};
        font-size: 9pt;
        font-weight: 600;
        letter-spacing: 0.6px;
    }}
    QLabel#cardValue {{
        color: {p.text};
        font-size: 24pt;
        font-weight: 650;
    }}
    QLabel#cardUnit {{
        color: {p.text_muted};
        font-size: 10pt;
        padding-bottom: 6px;
    }}
    QLabel#cardSubtitle, QLabel#muted {{
        color: {p.text_muted};
        font-size: 9pt;
    }}
    QLabel#faint {{
        color: {p.text_faint};
        font-size: 8.5pt;
    }}
    QLabel#sectionTitle {{
        color: {p.text};
        font-size: 11pt;
        font-weight: 600;
    }}
    QLabel#metricValue {{
        color: {p.text};
        font-size: 14pt;
        font-weight: 600;
    }}
    QLabel#metricLabel {{
        color: {p.text_muted};
        font-size: 8.5pt;
    }}
    QLabel#badgeSuccess {{
        background: rgba(34, 197, 94, 0.14);
        color: {p.success};
        border-radius: 9px;
        padding: 2px 8px;
        font-size: 8pt;
        font-weight: 600;
    }}
    QLabel#badgeWarning {{
        background: rgba(245, 158, 11, 0.14);
        color: {p.warning};
        border-radius: 9px;
        padding: 2px 8px;
        font-size: 8pt;
        font-weight: 600;
    }}
    QLabel#badgeCritical {{
        background: rgba(239, 68, 68, 0.14);
        color: {p.critical};
        border-radius: 9px;
        padding: 2px 8px;
        font-size: 8pt;
        font-weight: 600;
    }}
    QLabel#badgeInfo {{
        background: {p.accent_soft};
        color: {p.accent_hover};
        border-radius: 9px;
        padding: 2px 8px;
        font-size: 8pt;
        font-weight: 600;
    }}
    QLabel#badgeNeutral {{
        background: {p.card_alt};
        color: {p.text_muted};
        border: 1px solid {p.border};
        border-radius: 9px;
        padding: 2px 8px;
        font-size: 8pt;
    }}
    QFrame#card {{
        background-color: {p.card};
        border: 1px solid {p.border};
        border-radius: 14px;
    }}
    QFrame#card[accent="true"] {{
        border: 1px solid {p.border_strong};
    }}
    QFrame#innerCard {{
        background-color: {p.card_alt};
        border: 1px solid {p.border};
        border-radius: 10px;
    }}
    QFrame#statusPill {{
        background-color: {p.card_alt};
        border: 1px solid {p.border};
        border-radius: 12px;
    }}
    QFrame#divider {{
        background-color: {p.border};
        max-height: 1px;
        min-height: 1px;
        border: none;
    }}
    QFrame#warningBanner {{
        background-color: rgba(245, 158, 11, 0.10);
        border: 1px solid rgba(245, 158, 11, 0.35);
        border-radius: 10px;
    }}
    QFrame#dangerBanner {{
        background-color: rgba(239, 68, 68, 0.10);
        border: 1px solid rgba(239, 68, 68, 0.35);
        border-radius: 10px;
    }}
    QPushButton {{
        background-color: {p.card_alt};
        color: {p.text};
        border: 1px solid {p.border};
        border-radius: 8px;
        padding: 7px 14px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        border-color: {p.border_strong};
        background-color: {p.hover};
    }}
    QPushButton:pressed {{
        background-color: {p.border};
    }}
    QPushButton:disabled {{
        color: {p.text_faint};
        border-color: {p.border};
        background-color: transparent;
    }}
    QPushButton#primary {{
        background-color: {p.accent};
        border: 1px solid {p.accent};
        color: #FFFFFF;
        font-weight: 600;
    }}
    QPushButton#primary:hover {{
        background-color: {p.accent_hover};
        border-color: {p.accent_hover};
    }}
    QPushButton#primary:disabled {{
        background-color: {p.card_alt};
        color: {p.text_faint};
        border-color: {p.border};
    }}
    QPushButton#danger {{
        background-color: transparent;
        border: 1px solid rgba(239, 68, 68, 0.55);
        color: {p.critical};
    }}
    QPushButton#danger:hover {{
        background-color: rgba(239, 68, 68, 0.12);
    }}
    QPushButton#ghost {{
        background-color: transparent;
        border: 1px solid transparent;
        color: {p.text_muted};
        padding: 6px 10px;
    }}
    QPushButton#ghost:hover {{
        background-color: {p.hover};
        color: {p.text};
    }}
    QToolButton {{
        background-color: transparent;
        border: none;
        border-radius: 8px;
        padding: 6px;
        color: {p.text_muted};
    }}
    QToolButton:hover {{
        background-color: {p.hover};
        color: {p.text};
    }}
    QToolButton#navButton {{
        text-align: left;
        padding: 9px 12px;
        border-radius: 9px;
        color: {p.text_muted};
        font-size: 9.5pt;
        font-weight: 500;
    }}
    QToolButton#navButton:hover {{
        background-color: {p.hover};
        color: {p.text};
    }}
    QToolButton#navButton:checked {{
        background-color: {p.accent_soft};
        color: {p.text};
        font-weight: 600;
    }}
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        background-color: {p.card_alt};
        border: 1px solid {p.border};
        border-radius: 8px;
        padding: 6px 10px;
        color: {p.text};
        min-height: 18px;
    }}
    QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover {{
        border-color: {p.border_strong};
    }}
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
        border-color: {p.accent};
    }}
    QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {{
        color: {p.text_faint};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 22px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {p.card};
        border: 1px solid {p.border};
        border-radius: 8px;
        selection-background-color: {p.accent_soft};
        selection-color: {p.text};
        padding: 4px;
        outline: 0;
    }}
    QCheckBox {{
        color: {p.text};
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 4px;
        border: 1px solid {p.border_strong};
        background: {p.card_alt};
    }}
    QCheckBox::indicator:hover {{
        border-color: {p.accent};
    }}
    QCheckBox::indicator:checked {{
        background-color: {p.accent};
        border-color: {p.accent};
    }}
    QCheckBox::indicator:disabled {{
        border-color: {p.border};
        background: transparent;
    }}
    QProgressBar {{
        background-color: {p.card_alt};
        border: none;
        border-radius: 3px;
        max-height: 6px;
        min-height: 6px;
        text-align: center;
        color: transparent;
    }}
    QProgressBar::chunk {{
        border-radius: 3px;
        background-color: {p.accent};
    }}
    QTableView, QTreeView {{
        background-color: transparent;
        alternate-background-color: {p.card_alt};
        border: none;
        gridline-color: transparent;
        selection-background-color: {p.selection};
        selection-color: {p.text};
        color: {p.text};
    }}
    QTableView::item {{
        padding: 5px 8px;
        border: none;
    }}
    QTableView::item:selected {{
        background-color: {p.selection};
    }}
    QHeaderView {{
        background-color: transparent;
        border: none;
    }}
    QHeaderView::section {{
        background-color: transparent;
        color: {p.text_faint};
        border: none;
        border-bottom: 1px solid {p.border};
        padding: 7px 8px;
        font-size: 8.5pt;
        font-weight: 600;
        letter-spacing: 0.4px;
    }}
    QHeaderView::section:hover {{
        color: {p.text_muted};
    }}
    QTableCornerButton::section {{
        background: transparent;
        border: none;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 9px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {p.border_strong};
        border-radius: 4px;
        min-height: 28px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {p.text_faint};
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 9px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal {{
        background: {p.border_strong};
        border-radius: 4px;
        min-width: 28px;
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        width: 0;
        height: 0;
    }}
    QScrollBar::add-page, QScrollBar::sub-page {{
        background: transparent;
    }}
    QTabWidget::pane {{
        border: 1px solid {p.border};
        border-radius: 10px;
        top: -1px;
    }}
    QTabBar::tab {{
        background: transparent;
        color: {p.text_muted};
        padding: 7px 14px;
        border: none;
        border-bottom: 2px solid transparent;
    }}
    QTabBar::tab:selected {{
        color: {p.text};
        border-bottom: 2px solid {p.accent};
    }}
    QTabBar::tab:hover {{
        color: {p.text};
    }}
    QTextBrowser, QPlainTextEdit, QTextEdit {{
        background-color: {p.card};
        border: 1px solid {p.border};
        border-radius: 10px;
        color: {p.text};
        padding: 6px;
    }}
    QToolTip {{
        background-color: {p.card};
        color: {p.text};
        border: 1px solid {p.border_strong};
        padding: 5px 8px;
    }}
    QMenu {{
        background-color: {p.card};
        border: 1px solid {p.border};
        border-radius: 8px;
        padding: 6px;
    }}
    QMenu::item {{
        padding: 6px 18px;
        border-radius: 6px;
    }}
    QMenu::item:selected {{
        background-color: {p.accent_soft};
    }}
    QSplitter::handle {{
        background: transparent;
        width: 10px;
    }}
    QMessageBox {{
        background-color: {p.card};
    }}
    QMessageBox QLabel {{
        color: {p.text};
    }}
    QSlider::groove:horizontal {{
        height: 4px;
        background: {p.border};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {p.accent};
        width: 14px;
        height: 14px;
        margin: -5px 0;
        border-radius: 7px;
    }}
    QSlider::sub-page:horizontal {{
        background: {p.accent};
        border-radius: 2px;
    }}
    """
    return qss


def color(value: str) -> QColor:
    return QColor(value)
