"""Data sources manager panel."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from bimap.models.data_source import DataSource


class DataPanel(QWidget):
    """
    Lists configured data sources and lets the user add/edit/remove/refresh them.

    Signals
    -------
    add_requested()
    edit_requested(source_id_str)
    remove_requested(source_id_str)
    refresh_requested(source_id_str)
    """

    add_requested = pyqtSignal()
    edit_requested = pyqtSignal(str)
    remove_requested = pyqtSignal(str)
    refresh_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._project = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 4, 2, 4)

        title = QLabel("Data Sources")
        title.setStyleSheet("font-weight: bold; padding: 2px;")
        layout.addWidget(title)

        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self._list)

        btn_row1 = QHBoxLayout()
        btn_add = QPushButton("+ Add")
        btn_add.clicked.connect(self.add_requested)
        btn_edit = QPushButton("Edit")
        btn_edit.clicked.connect(self._on_edit)
        btn_row1.addWidget(btn_add)
        btn_row1.addWidget(btn_edit)
        layout.addLayout(btn_row1)

        btn_row2 = QHBoxLayout()
        btn_refresh = QPushButton("Refresh Now")
        btn_refresh.clicked.connect(self._on_refresh)
        btn_remove = QPushButton("Remove")
        btn_remove.clicked.connect(self._on_remove)
        btn_row2.addWidget(btn_refresh)
        btn_row2.addWidget(btn_remove)
        layout.addLayout(btn_row2)

    def refresh(self, project: Any) -> None:
        self._project = project
        self._list.clear()
        for ds in project.data_sources:
            status = "✓" if not ds.last_error else "✗"
            label = f"{status} {ds.name}  [{ds.source_type}]"
            it = QListWidgetItem(label)
            it.setData(Qt.ItemDataRole.UserRole, str(ds.id))
            if ds.last_error:
                it.setForeground(Qt.GlobalColor.red)
            self._list.addItem(it)

    def update_source_status(self, source_id: str, error: str = "") -> None:
        for i in range(self._list.count()):
            it = self._list.item(i)
            if it and it.data(Qt.ItemDataRole.UserRole) == source_id:
                if error:
                    it.setText(f"✗ {it.text().lstrip('✓✗ ')}")
                    it.setForeground(Qt.GlobalColor.red)
                else:
                    it.setText(f"✓ {it.text().lstrip('✓✗ ')}")
                    it.setForeground(Qt.GlobalColor.black)

    def _selected_id(self) -> str | None:
        selected = self._list.selectedItems()
        if selected:
            return selected[0].data(Qt.ItemDataRole.UserRole)
        return None

    def _on_edit(self) -> None:
        sid = self._selected_id()
        if sid:
            self.edit_requested.emit(sid)

    def _on_remove(self) -> None:
        sid = self._selected_id()
        if sid:
            self.remove_requested.emit(sid)

    def _on_refresh(self) -> None:
        sid = self._selected_id()
        if sid:
            self.refresh_requested.emit(sid)
