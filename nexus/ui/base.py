"""Base class for stack pages."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from nexus.ui.context import AppContext


class BasePage(QWidget):
    navigateRequested = Signal(str)

    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("pageRoot")
        self.context = context
        self.context.monitoring.snapshotReady.connect(self.on_snapshot)

    # -- page contract ------------------------------------------------------
    title = "Page"
    subtitle = ""

    def on_snapshot(self, snapshot) -> None:
        """Called on the GUI thread for every new metrics snapshot."""

    def on_activated(self) -> None:
        """Called when the page becomes visible."""

    def on_deactivated(self) -> None:
        """Called when the page is hidden; stop expensive work here."""

    def refresh_now(self) -> None:
        """Handle an explicit user refresh request."""

    def refresh_theme(self) -> None:
        """Re-apply painted colours after a theme change."""
