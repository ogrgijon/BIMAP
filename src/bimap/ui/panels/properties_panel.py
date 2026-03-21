"""Properties panel — edit properties of the currently selected element."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFontComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from bimap.models.annotation import Annotation
from bimap.models.keypoint import Keypoint
from bimap.models.zone import Zone


class ColorButton(QPushButton):
    """A color-swatch button that shows the hex value and opens a full color picker."""

    color_changed = pyqtSignal(str)

    def __init__(self, color: str = "#3388FF", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = color
        self.setFixedHeight(28)
        self.setMinimumWidth(90)
        self._update_style()
        self.clicked.connect(self._pick_color)

    def set_color(self, color: str) -> None:
        self._color = color
        self._update_style()

    def color(self) -> str:
        return self._color

    def _update_style(self) -> None:
        # Choose a contrasting label colour (dark or light) based on luminance
        c = QColor(self._color)
        luminance = 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()
        label_color = "#111111" if luminance > 140 else "#FFFFFF"
        self.setText(self._color.upper())
        self.setStyleSheet(
            f"background-color: {self._color};"
            f"color: {label_color};"
            "border: 1px solid #666;"
            "border-radius: 4px;"
            "font-size: 10px;"
            "font-family: monospace;"
            "padding: 0 4px;"
        )

    def _pick_color(self) -> None:
        options = QColorDialog.ColorDialogOption.ShowAlphaChannel
        col = QColorDialog.getColor(
            QColor(self._color), self, "Choose Color", options=options
        )
        if col.isValid():
            self._color = col.name()   # no alpha in hex; alpha handled separately
            self._update_style()
            self.color_changed.emit(self._color)


class PropertiesPanel(QWidget):
    """
    Dynamic panel showing editable properties for the selected element.

    Signals
    -------
    element_changed(element_type, element_id, field, value) — a field was edited
    """

    element_changed = pyqtSignal(str, str, str, object)
    # Emitted when user applies a style preset: (element_type, element_id, preset_name)
    preset_applied = pyqtSignal(str, str, str)
    # Emitted when a metadata key-value pair changes: (element_type, element_id, key, value|None)
    metadata_changed = pyqtSignal(str, str, str, object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._element: Any = None
        self._etype: str = ""
        self._project: Any = None
        self._setup_ui()

    def set_project(self, project: Any) -> None:
        """Supply the current project so presets can be listed."""
        self._project = project

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 6, 4, 4)
        outer.setSpacing(4)

        self._title = QLabel("Properties")
        self._title.setStyleSheet(
            "font-weight: bold; font-size: 12px;"
            "padding: 3px 4px;"
            "background: #252526;"
            "color: #9CDCFE;"
            "border-bottom: 1px solid #3C3C3C;"
        )
        outer.addWidget(self._title)

        # ── Tab widget ──────────────────────────────────────────────────────── #
        self._tabs = QTabWidget()
        outer.addWidget(self._tabs)

        # Tab 0: Style (scroll area wrapping the form)
        style_tab = QWidget()
        style_vbox = QVBoxLayout(style_tab)
        style_vbox.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        style_vbox.addWidget(scroll)

        self._content = QWidget()
        self._form = QFormLayout(self._content)
        self._form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self._form.setVerticalSpacing(6)
        self._form.setContentsMargins(4, 4, 4, 4)
        self._content.setStyleSheet(
            "QGroupBox {"
            "  font-weight: bold;"
            "  font-size: 11px;"
            "  border: 1px solid #3C3C3C;"
            "  border-radius: 4px;"
            "  margin-top: 8px;"
            "  padding-top: 4px;"
            "}"
            "QGroupBox::title {"
            "  subcontrol-origin: margin;"
            "  subcontrol-position: top left;"
            "  padding: 0 4px;"
            "  color: #AAAAAA;"
            "}"
        )
        scroll.setWidget(self._content)

        # Tab 1: Metadata (direct layout, no extra scroll needed)
        self._meta_tab = QWidget()
        self._meta_layout = QVBoxLayout(self._meta_tab)
        self._meta_layout.setContentsMargins(6, 6, 6, 6)
        self._meta_layout.setSpacing(6)
        _empty = QLabel("Select an element to view its metadata.")
        _empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _empty.setStyleSheet("color: #888888; font-style: italic;")
        self._meta_layout.addWidget(_empty)
        self._meta_layout.addStretch()

        self._tabs.addTab(style_tab, "Style")
        self._tabs.addTab(self._meta_tab, "Metadata")

    def show_element(self, element: Any, etype: str) -> None:
        self._element = element
        self._etype = etype
        self._clear_form()
        if etype == "zone":
            self._populate_zone(element)
        elif etype == "keypoint":
            self._populate_keypoint(element)
        elif etype == "annotation":
            self._populate_annotation(element)

    def clear(self) -> None:
        self._element = None
        self._etype = ""
        self._clear_form()
        self._title.setText("Properties")

    # ── Form builders ──────────────────────────────────────────────────────────

    def _clear_form(self) -> None:
        while self._form.rowCount() > 0:
            self._form.removeRow(0)
        # Clear metadata tab content
        while self._meta_layout.count() > 0:
            item = self._meta_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _populate_zone(self, zone: "Zone") -> None:
        self._title.setText(f"Zone: {zone.name}")

        # Style presets (only shown if the project has any)
        presets = getattr(self._project, "style_presets", []) if self._project else []
        if presets:
            preset_combo = QComboBox()
            preset_combo.addItem("— Apply Preset —")
            for p in presets:
                preset_combo.addItem(p.name)
            preset_combo.currentIndexChanged.connect(
                lambda idx: (
                    self.preset_applied.emit(self._etype, str(zone.id), presets[idx - 1].name)
                    if idx > 0 and self._element
                    else None
                )
            )
            self._form.addRow("Preset", preset_combo)
        name_edit = self._add_line_edit("Name", zone.name)
        name_edit.editingFinished.connect(
            lambda: self._emit("name", name_edit.text())
        )
        group_edit = self._add_line_edit("Group", zone.group)
        group_edit.editingFinished.connect(
            lambda: self._emit("group", group_edit.text())
        )

        # Style section
        bg = QGroupBox("Fill")
        bg_layout = QFormLayout(bg)
        fill_btn = ColorButton(zone.style.fill_color)
        fill_btn.color_changed.connect(lambda c: self._emit("style.fill_color", c))
        bg_layout.addRow("Color", fill_btn)

        alpha_slider = QSlider(Qt.Orientation.Horizontal)
        alpha_slider.setRange(0, 255)
        alpha_slider.setValue(zone.style.fill_alpha)
        alpha_slider.valueChanged.connect(lambda v: self._emit("style.fill_alpha", v))
        bg_layout.addRow("Opacity", alpha_slider)
        self._form.addRow(bg)

        border_grp = QGroupBox("Border")
        border_layout = QFormLayout(border_grp)
        border_btn = ColorButton(zone.style.border_color)
        border_btn.color_changed.connect(lambda c: self._emit("style.border_color", c))
        border_layout.addRow("Color", border_btn)
        bw_spin = QSpinBox()
        bw_spin.setRange(0, 20)
        bw_spin.setValue(zone.style.border_width)
        bw_spin.valueChanged.connect(lambda v: self._emit("style.border_width", v))
        border_layout.addRow("Width", bw_spin)
        self._form.addRow(border_grp)

        label_grp = QGroupBox("Label")
        label_layout = QFormLayout(label_grp)
        no_label = not bool(zone.label.text)
        label_grp.setEnabled(True)  # allow text entry even when empty

        lbl_edit = QLineEdit(zone.label.text)
        lbl_edit.editingFinished.connect(
            lambda: self._emit("label.text", lbl_edit.text())
        )
        label_layout.addRow("Text", lbl_edit)

        font_combo = QFontComboBox()
        font_combo.setCurrentFont(QFont(zone.label.style.font_family))
        font_combo.currentFontChanged.connect(
            lambda f: self._emit("label.style.font_family", f.family())
        )
        label_layout.addRow("Font", font_combo)

        fs_spin = QSpinBox()
        fs_spin.setRange(6, 72)
        fs_spin.setValue(zone.label.style.font_size)
        fs_spin.valueChanged.connect(lambda v: self._emit("label.style.font_size", v))
        label_layout.addRow("Size", fs_spin)

        style_row_widget = QWidget()
        style_row = QHBoxLayout(style_row_widget)
        style_row.setContentsMargins(0, 0, 0, 0)
        bold_cb = QCheckBox("Bold")
        bold_cb.setChecked(zone.label.style.bold)
        bold_cb.toggled.connect(lambda v: self._emit("label.style.bold", v))
        italic_cb = QCheckBox("Italic")
        italic_cb.setChecked(zone.label.style.italic)
        italic_cb.toggled.connect(lambda v: self._emit("label.style.italic", v))
        style_row.addWidget(bold_cb)
        style_row.addWidget(italic_cb)
        label_layout.addRow("Style", style_row_widget)

        txt_color_btn = ColorButton(zone.label.style.color)
        txt_color_btn.color_changed.connect(lambda c: self._emit("label.style.color", c))
        label_layout.addRow("Color", txt_color_btn)

        bg_color_btn = ColorButton(zone.label.style.background_color or "#FFFFFF")
        bg_color_btn.color_changed.connect(
            lambda c: self._emit("label.style.background_color", c)
        )
        label_layout.addRow("Bg Color", bg_color_btn)

        ox_spin = QDoubleSpinBox()
        ox_spin.setRange(-200.0, 200.0)
        ox_spin.setValue(zone.label.offset_x)
        ox_spin.valueChanged.connect(lambda v: self._emit("label.offset_x", v))
        label_layout.addRow("Offset X", ox_spin)

        oy_spin = QDoubleSpinBox()
        oy_spin.setRange(-200.0, 200.0)
        oy_spin.setValue(zone.label.offset_y)
        oy_spin.valueChanged.connect(lambda v: self._emit("label.offset_y", v))
        label_layout.addRow("Offset Y", oy_spin)

        self._form.addRow(label_grp)
        self._setup_metadata_tab(zone.metadata, zone)

    def _setup_metadata_tab(self, metadata: dict, element: Any) -> None:
        """Populate the Metadata tab with an editable key-value table."""
        # Clear existing tab content first
        while self._meta_layout.count() > 0:
            item = self._meta_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(["Key", "Value"])
        table.horizontalHeader().setStretchLastSection(True)
        table.setAlternatingRowColors(True)
        from PyQt6.QtWidgets import QSizePolicy
        table.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        def _load() -> None:
            table.blockSignals(True)
            table.setRowCount(0)
            for k, v in metadata.items():
                row = table.rowCount()
                table.insertRow(row)
                table.setItem(row, 0, QTableWidgetItem(k))
                table.setItem(row, 1, QTableWidgetItem(v))
            table.blockSignals(False)

        _load()

        def _on_cell_changed(r: int, c: int) -> None:
            k_item = table.item(r, 0)
            v_item = table.item(r, 1)
            if k_item is None:
                return
            key = k_item.text().strip()
            val = v_item.text() if v_item else ""
            if key:
                self.metadata_changed.emit(self._etype, str(element.id), key, val)

        table.cellChanged.connect(_on_cell_changed)
        self._meta_layout.addWidget(table)

        # ── Add row ──────────────────────────────────────────────────────── #
        btn_row = QHBoxLayout()
        key_combo = QComboBox()
        key_combo.setEditable(True)
        key_combo.setPlaceholderText("Key")
        key_combo.setMinimumWidth(100)
        layer_name = getattr(element, "layer", "Default")
        if self._project:
            for lyr in getattr(self._project, "layers", []):
                if lyr.name == layer_name:
                    for k in lyr.key_library:
                        if key_combo.findText(k) < 0:
                            key_combo.addItem(k)
                    break
        val_edit = QLineEdit()
        val_edit.setPlaceholderText("Value")
        btn_add = QPushButton("+ Add")

        def _add_row() -> None:
            key = key_combo.currentText().strip()
            val = val_edit.text()
            if not key:
                return
            self.metadata_changed.emit(self._etype, str(element.id), key, val)
            metadata[key] = val
            _load()
            key_combo.clearEditText()
            val_edit.clear()

        btn_add.clicked.connect(_add_row)
        btn_row.addWidget(key_combo)
        btn_row.addWidget(val_edit)
        btn_row.addWidget(btn_add)
        self._meta_layout.addLayout(btn_row)

        btn_rm = QPushButton("Remove Selected")

        def _remove_row() -> None:
            rows = {i.row() for i in table.selectedItems()}
            for r in sorted(rows, reverse=True):
                k_item = table.item(r, 0)
                if k_item:
                    self.metadata_changed.emit(
                        self._etype, str(element.id), k_item.text(), None
                    )
                    metadata.pop(k_item.text(), None)
                table.removeRow(r)

        btn_rm.clicked.connect(_remove_row)
        self._meta_layout.addWidget(btn_rm)

    def _populate_keypoint(self, kp: "Keypoint") -> None:
        self._title.setText("Keypoint")

        title_edit = self._add_line_edit("Title", kp.info_card.title)
        title_edit.editingFinished.connect(
            lambda: self._emit("info_card.title", title_edit.text())
        )
        sub_edit = self._add_line_edit("Subtitle", kp.info_card.subtitle)
        sub_edit.editingFinished.connect(
            lambda: self._emit("info_card.subtitle", sub_edit.text())
        )
        notes = QTextEdit(kp.info_card.notes)
        notes.setMaximumHeight(80)
        notes.textChanged.connect(lambda: self._emit("info_card.notes", notes.toPlainText()))
        self._form.addRow("Notes", notes)
        url_edit = self._add_line_edit("URL", kp.info_card.link_url)
        url_edit.editingFinished.connect(
            lambda: self._emit("info_card.link_url", url_edit.text())
        )

        color_btn = ColorButton(kp.icon_color)
        color_btn.color_changed.connect(lambda c: self._emit("icon_color", c))
        self._form.addRow("Pin Color", color_btn)

        size_spin = QSpinBox()
        size_spin.setRange(8, 40)
        size_spin.setValue(kp.icon_size)
        size_spin.valueChanged.connect(lambda v: self._emit("icon_size", v))
        self._form.addRow("Pin Size", size_spin)

        lat_spin = QDoubleSpinBox()
        lat_spin.setDecimals(6)
        lat_spin.setRange(-90, 90)
        lat_spin.setValue(kp.lat)
        lat_spin.valueChanged.connect(lambda v: self._emit("lat", v))
        self._form.addRow("Latitude", lat_spin)

        lon_spin = QDoubleSpinBox()
        lon_spin.setDecimals(6)
        lon_spin.setRange(-180, 180)
        lon_spin.setValue(kp.lon)
        lon_spin.valueChanged.connect(lambda v: self._emit("lon", v))
        self._form.addRow("Longitude", lon_spin)

        self._setup_metadata_tab(kp.metadata, kp)

    def _populate_annotation(self, ann: "Annotation") -> None:
        self._title.setText("Annotation")
        content = QTextEdit(ann.content)
        content.setMinimumHeight(60)
        content.textChanged.connect(lambda: self._emit("content", content.toPlainText()))
        self._form.addRow("Text", content)

        fs_spin = QSpinBox()
        fs_spin.setRange(6, 72)
        fs_spin.setValue(ann.style.font_size)
        fs_spin.valueChanged.connect(lambda v: self._emit("style.font_size", v))
        self._form.addRow("Font Size", fs_spin)

        color_btn = ColorButton(ann.style.color)
        color_btn.color_changed.connect(lambda c: self._emit("style.color", c))
        self._form.addRow("Text Color", color_btn)

        bg_btn = ColorButton(ann.style.background_color)
        bg_btn.color_changed.connect(lambda c: self._emit("style.background_color", c))
        self._form.addRow("Background", bg_btn)

        if hasattr(ann, "metadata"):
            self._setup_metadata_tab(ann.metadata, ann)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _add_line_edit(self, label: str, value: str) -> QLineEdit:
        edit = QLineEdit(value)
        self._form.addRow(label, edit)
        return edit

    def _emit(self, field: str, value: Any) -> None:
        if self._element:
            self.element_changed.emit(self._etype, str(self._element.id), field, value)

