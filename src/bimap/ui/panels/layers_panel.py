"""Layers panel — shows map elements organised by layer."""

from __future__ import annotations

import csv
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# UserRole data stored on tree items
_ROLE = Qt.ItemDataRole.UserRole


class _LayerTree(QTreeWidget):
    """QTreeWidget that intercepts drops to handle layer reassignment."""

    item_layer_changed = pyqtSignal(str, str, str)  # etype, eid, new_layer_name

    def dropEvent(self, event) -> None:  # type: ignore[override]
        dragged = self.currentItem()
        if dragged is None:
            event.ignore()
            return
        d = dragged.data(0, _ROLE)
        if not d or d[0] == "_layer":
            event.ignore()
            return
        etype, eid = d

        # Find the layer item under the drop position
        drop_pos = event.position().toPoint()
        target = self.itemAt(drop_pos)
        if target is None:
            event.ignore()
            return
        while target.parent() is not None:
            target = target.parent()
        layer_data = target.data(0, _ROLE)
        if not layer_data or layer_data[0] != "_layer":
            event.ignore()
            return

        self.item_layer_changed.emit(etype, eid, layer_data[1])
        event.accept()  # caller calls refresh() — don't let Qt re-order raw items


class LayersPanel(QWidget):
    """
    Tree panel listing map elements grouped by layer.

    Signals
    -------
    element_selected(element_type, id_str)
    element_visibility_changed(element_type, id_str, visible)
    element_delete_requested(element_type, id_str)
    layer_visibility_changed(layer_name, visible)
    layer_add_requested()
    layer_remove_requested(layer_name)
    """

    element_selected = pyqtSignal(str, str)
    element_visibility_changed = pyqtSignal(str, str, bool)
    element_delete_requested = pyqtSignal(str, str)
    layer_visibility_changed = pyqtSignal(str, bool)
    layer_add_requested = pyqtSignal()
    layer_remove_requested = pyqtSignal(str)
    element_action_requested = pyqtSignal(str, str, str)  # action, etype, eid
    element_layer_changed = pyqtSignal(str, str, str)     # etype, eid, new_layer

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._project: Any = None
        self._setup_ui()

    # ── UI setup ──────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 4, 2, 4)
        layout.setSpacing(4)

        header = QLabel("Layers")
        header.setStyleSheet("font-weight: bold; padding: 2px;")
        layout.addWidget(header)

        self._tree = _LayerTree()
        self._tree.setHeaderHidden(True)
        self._tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._tree.setDragEnabled(True)
        self._tree.setAcceptDrops(True)
        self._tree.setDropIndicatorShown(True)
        self._tree.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.itemClicked.connect(self._on_item_clicked)
        self._tree.itemChanged.connect(self._on_item_changed)
        self._tree.customContextMenuRequested.connect(self._on_context_menu)
        self._tree.item_layer_changed.connect(self.element_layer_changed)
        layout.addWidget(self._tree)

        row1 = QHBoxLayout()
        btn_add = QPushButton("+ Layer")
        btn_add.setToolTip("Add a new layer")
        btn_add.clicked.connect(self.layer_add_requested)
        row1.addWidget(btn_add)
        layout.addLayout(row1)

        btn_csv = QPushButton("Export Layer CSV…")
        btn_csv.setToolTip("Export elements of the selected layer to CSV")
        btn_csv.clicked.connect(self._on_export_csv)
        layout.addWidget(btn_csv)

    # ── Public API ────────────────────────────────────────────────────────────

    def refresh(self, project: Any) -> None:
        """Rebuild the entire tree from *project*."""
        self._project = project

        self._tree.blockSignals(True)
        self._tree.clear()

        # Build layer→elements mapping preserving layer order from project
        layer_elements: dict[str, list[tuple[str, Any]]] = {}
        for layer in project.layers:
            layer_elements[layer.name] = []

        # Distribute elements; unknown layers get appended on the fly
        for zone in project.zones:
            ln = getattr(zone, "layer", "Default")
            layer_elements.setdefault(ln, []).append(("zone", zone))

        for kp in project.keypoints:
            ln = getattr(kp, "layer", "Default")
            layer_elements.setdefault(ln, []).append(("keypoint", kp))

        for ann in project.annotations:
            ln = getattr(ann, "layer", "Default")
            layer_elements.setdefault(ln, []).append(("annotation", ann))

        layer_visible = {lyr.name: lyr.visible for lyr in project.layers}

        bold = QFont()
        bold.setBold(True)

        for layer_name, elements in layer_elements.items():
            layer_item = QTreeWidgetItem([layer_name])
            layer_item.setData(0, _ROLE, ("_layer", layer_name))
            visible = layer_visible.get(layer_name, True)
            layer_item.setCheckState(0, Qt.CheckState.Checked if visible else Qt.CheckState.Unchecked)
            layer_item.setFlags(
                layer_item.flags()
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsEnabled
            )
            layer_item.setFont(0, bold)
            self._tree.addTopLevelItem(layer_item)
            layer_item.setExpanded(True)

            for etype, elem in elements:
                if etype == "zone":
                    label = elem.name
                elif etype == "keypoint":
                    label = elem.info_card.title or "Pin"
                else:
                    label = (elem.content[:30] if elem.content else "") or str(elem.ann_type)

                child = QTreeWidgetItem([f"  {label}"])
                child.setData(0, _ROLE, (etype, str(elem.id)))
                child.setCheckState(
                    0,
                    Qt.CheckState.Checked if getattr(elem, "visible", True) else Qt.CheckState.Unchecked,
                )
                child.setFlags(
                    child.flags()
                    | Qt.ItemFlag.ItemIsUserCheckable
                    | Qt.ItemFlag.ItemIsEnabled
                )
                layer_item.addChild(child)

        self._tree.blockSignals(False)

    def select_element(self, element_type: str, element_id: str) -> None:
        """Programmatically highlight an element row in the tree."""
        for i in range(self._tree.topLevelItemCount()):
            layer_item = self._tree.topLevelItem(i)
            if layer_item is None:
                continue
            for j in range(layer_item.childCount()):
                child = layer_item.child(j)
                d = child.data(0, _ROLE) if child else None
                if d and d[0] == element_type and d[1] == element_id:
                    self._tree.setCurrentItem(child)
                    return


    def _on_item_clicked(self, item: QTreeWidgetItem | None, _column: int) -> None:
        if item is None:
            return
        data = item.data(0, _ROLE)
        if data and data[0] != "_layer":
            etype, eid = data
            self.element_selected.emit(etype, eid)

    def _on_item_changed(self, item: QTreeWidgetItem | None, _column: int) -> None:
        if item is None:
            return
        data = item.data(0, _ROLE)
        if not data:
            return
        kind, id_or_name = data
        visible = item.checkState(0) == Qt.CheckState.Checked
        if kind == "_layer":
            self.layer_visibility_changed.emit(id_or_name, visible)
        else:
            self.element_visibility_changed.emit(kind, id_or_name, visible)

    def _on_remove_layer(self) -> None:
        item = self._tree.currentItem()
        if item is None:
            return
        # Navigate to the top-level layer item if a child is selected
        parent = item.parent()
        if parent is not None:
            item = parent
        data = item.data(0, _ROLE)
        if not data or data[0] != "_layer":
            return
        layer_name = data[1]
        if layer_name == "Default":
            QMessageBox.warning(self, "Cannot Remove", "The 'Default' layer cannot be removed.")
            return
        self.layer_remove_requested.emit(layer_name)

    def _on_context_menu(self, pos) -> None:
        """Right-click context menu for layers (remove) and elements (go_to/edit/remove/update)."""
        item = self._tree.itemAt(pos)
        if item is None:
            return
        d = item.data(0, _ROLE)
        if not d:
            return
        menu = QMenu(self)
        if d[0] == "_layer":
            layer_name = d[1]
            act_remove = menu.addAction("🗑  Remove Layer…")
            chosen = menu.exec(self._tree.mapToGlobal(pos))
            if chosen == act_remove:
                if layer_name == "Default":
                    QMessageBox.warning(self, "Cannot Remove",
                                        "The 'Default' layer cannot be removed.")
                    return
                self.layer_remove_requested.emit(layer_name)
        else:
            etype, eid = d
            act_goto   = menu.addAction("🎯  Go to")
            act_edit   = menu.addAction("✏  Edit…")
            act_update = menu.addAction("🔄  Update")
            menu.addSeparator()
            act_remove = menu.addAction("🗑  Remove…")
            chosen = menu.exec(self._tree.mapToGlobal(pos))
            if chosen == act_goto:
                self.element_action_requested.emit("go_to", etype, eid)
            elif chosen == act_edit:
                self.element_action_requested.emit("edit", etype, eid)
            elif chosen == act_update:
                self.element_action_requested.emit("update", etype, eid)
            elif chosen == act_remove:
                self.element_action_requested.emit("remove", etype, eid)

    def _on_export_csv(self) -> None:
        """Export elements of the currently selected layer to CSV."""
        item = self._tree.currentItem()
        if item is None:
            QMessageBox.information(self, "No Selection", "Select a layer first.")
            return
        parent = item.parent()
        if parent is not None:
            item = parent
        data = item.data(0, _ROLE)
        if not data or data[0] != "_layer":
            QMessageBox.information(self, "No Layer", "Select a layer node to export.")
            return
        self._export_layer_csv(data[1])

    def _export_layer_csv(self, layer_name: str) -> None:
        if self._project is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            f"Export '{layer_name}' to CSV",
            f"{layer_name}.csv",
            "CSV Files (*.csv)",
        )
        if not path:
            return

        rows: list[dict[str, object]] = []

        for zone in self._project.zones:
            if getattr(zone, "layer", "Default") == layer_name:
                lat = zone.coordinates[0].lat if zone.coordinates else ""
                lon = zone.coordinates[0].lon if zone.coordinates else ""
                rows.append({"type": "zone", "name": zone.name, "lat": lat, "lon": lon, "layer": layer_name})

        for kp in self._project.keypoints:
            if getattr(kp, "layer", "Default") == layer_name:
                rows.append({"type": "keypoint", "name": kp.info_card.title or "Pin",
                              "lat": kp.lat, "lon": kp.lon, "layer": layer_name})

        for ann in self._project.annotations:
            if getattr(ann, "layer", "Default") == layer_name:
                rows.append({"type": "annotation", "name": ann.content[:60],
                              "lat": ann.anchor_lat or "", "lon": ann.anchor_lon or "",
                              "layer": layer_name})

        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=["type", "name", "lat", "lon", "layer"])
            writer.writeheader()
            writer.writerows(rows)

        QMessageBox.information(
            self, "CSV Exported", f"Exported {len(rows)} element(s) to:\n{path}"
        )

