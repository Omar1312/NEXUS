"""Generic record table model, search proxy and table configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableView

SORT_ROLE = int(Qt.ItemDataRole.UserRole) + 1


@dataclass(frozen=True, slots=True)
class Column:
    header: str
    getter: Callable[[Any], Any]
    formatter: Callable[[Any], str] | None = None
    align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    width: int | None = None
    color: Callable[[Any], str | None] | None = None
    tooltip: Callable[[Any], str] | None = None

    def display(self, record: Any) -> str:
        value = self.getter(record)
        if self.formatter is not None:
            try:
                return self.formatter(value)
            except Exception:
                return str(value)
        return "" if value is None else str(value)


class RecordsModel(QAbstractTableModel):
    def __init__(self, columns: Sequence[Column], parent=None) -> None:
        super().__init__(parent)
        self._columns = list(columns)
        self._records: list[Any] = []

    @property
    def columns(self) -> list[Column]:
        return self._columns

    def set_records(self, records: Sequence[Any]) -> None:
        self.beginResetModel()
        self._records = list(records)
        self.endResetModel()

    def record_at(self, row: int) -> Any | None:
        if 0 <= row < len(self._records):
            return self._records[row]
        return None

    def search_text(self, row: int) -> str:
        if not (0 <= row < len(self._records)):
            return ""
        record = self._records[row]
        parts = [column.display(record) for column in self._columns]
        return " ".join(parts).lower()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._records)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._columns)

    def data(self, index: QModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)):
        if not index.isValid() or not (0 <= index.row() < len(self._records)):
            return None
        record = self._records[index.row()]
        column = self._columns[index.column()]
        if role == int(Qt.ItemDataRole.DisplayRole):
            return column.display(record)
        if role == SORT_ROLE:
            return column.getter(record)
        if role == int(Qt.ItemDataRole.TextAlignmentRole):
            return int(column.align)
        if role == int(Qt.ItemDataRole.ForegroundRole) and column.color is not None:
            color = column.color(record)
            return QColor(color) if color else None
        if role == int(Qt.ItemDataRole.ToolTipRole):
            if column.tooltip is not None:
                return column.tooltip(record)
            value = column.getter(record)
            return "" if value is None else str(value)
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = int(Qt.ItemDataRole.DisplayRole)):  # noqa: N802
        if orientation == Qt.Orientation.Horizontal and role == int(Qt.ItemDataRole.DisplayRole):
            if 0 <= section < len(self._columns):
                return self._columns[section].header
        return None


class SearchProxy(QSortFilterProxyModel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._query = ""
        self.setSortRole(SORT_ROLE)
        self.setDynamicSortFilter(True)
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def set_query(self, text: str) -> None:
        self._query = text.strip().lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:  # noqa: N802
        if not self._query:
            return True
        model = self.sourceModel()
        if isinstance(model, RecordsModel):
            return self._query in model.search_text(source_row)
        for column in range(model.columnCount()):
            index = model.index(source_row, column, source_parent)
            value = model.data(index, int(Qt.ItemDataRole.DisplayRole))
            if value and self._query in str(value).lower():
                return True
        return False

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:  # noqa: N802
        left_value = left.data(SORT_ROLE)
        right_value = right.data(SORT_ROLE)
        if left_value is None and right_value is None:
            return False
        if left_value is None:
            return False
        if right_value is None:
            return True
        try:
            return left_value < right_value
        except TypeError:
            return str(left_value).lower() < str(right_value).lower()


def configure_table(view: QTableView, model: RecordsModel, proxy: SearchProxy | None = None) -> None:
    view.setModel(proxy or model)
    view.setSortingEnabled(True)
    view.setShowGrid(False)
    view.setAlternatingRowColors(True)
    view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    view.setWordWrap(False)
    view.setTextElideMode(Qt.TextElideMode.ElideRight)
    view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    view.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    view.verticalHeader().setVisible(False)
    view.verticalHeader().setDefaultSectionSize(30)
    header = view.horizontalHeader()
    header.setHighlightSections(False)
    header.setSectionsClickable(True)
    header.setStretchLastSection(True)
    header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    for index, column in enumerate(model.columns):
        if column.width:
            view.setColumnWidth(index, column.width)
