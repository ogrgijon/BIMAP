"""Extension Library Manager dialog.

Lets the user browse, create, edit, and delete reusable HTML5/CSS/JS
extension templates that are stored in the project's ``extension_library``.
From the Properties panel the user can then pick a template from the library
and assign it to any zone or keypoint.
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from bimap.i18n import t
from bimap.models.extension_template import ExtensionTemplate


class ExtensionManagerDialog(QDialog):
    """Full CRUD interface for the project's extension library.

    After ``exec()`` the caller should inspect ``self.library`` and persist
    it back to ``project.extension_library``.
    """

    def __init__(
        self,
        library: list[ExtensionTemplate],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        import copy
        self.library: list[ExtensionTemplate] = copy.deepcopy(library)
        self._current_idx: int = -1
        self.setWindowTitle(t("Extension Library"))
        self.setMinimumSize(900, 580)
        self._setup_ui()
        self._refresh_list()

    # ── UI ──────────────────────────────────────────────────────────────────── #

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # ── Left: list + CRUD buttons ────────────────────────────────────── #
        left = QWidget()
        left.setMinimumWidth(200)
        left.setMaximumWidth(260)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 4, 0)
        lv.setSpacing(6)

        lbl = QLabel(t("Extension Library"))
        lbl.setStyleSheet("font-weight: bold; color: #9CDCFE;")
        lv.addWidget(lbl)

        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_row_changed)
        lv.addWidget(self._list, 1)

        btn_new = QPushButton(t("New Extension"))
        btn_new.clicked.connect(self._new_extension)
        btn_del = QPushButton(t("Delete Extension"))
        btn_del.clicked.connect(self._delete_extension)
        lv.addWidget(btn_new)
        lv.addWidget(btn_del)

        splitter.addWidget(left)

        # ── Right: editor ────────────────────────────────────────────────── #
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(4, 0, 0, 0)
        rv.setSpacing(6)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText(t("Extension Name"))
        self._name_edit.textChanged.connect(self._on_name_changed)

        self._desc_edit = QLineEdit()
        self._desc_edit.setPlaceholderText(t("Extension Description"))
        self._desc_edit.textChanged.connect(self._on_desc_changed)

        rv.addWidget(QLabel(t("Name")))
        rv.addWidget(self._name_edit)
        rv.addWidget(QLabel(t("Description")))
        rv.addWidget(self._desc_edit)
        rv.addWidget(QLabel("HTML / CSS / JS"))

        self._html_edit = QPlainTextEdit()
        mono = QFont("Consolas", 10)
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self._html_edit.setFont(mono)
        self._html_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._html_edit.setStyleSheet(
            "background: #1e1e1e; color: #d4d4d4;"
            "border: 1px solid #3C3C3C;"
        )
        self._html_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._html_edit.textChanged.connect(self._on_html_changed)
        rv.addWidget(self._html_edit, 1)

        self._empty_label = QLabel(t("No extensions in library."))
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet("color: #888888; font-style: italic;")
        rv.addWidget(self._empty_label)

        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 1)

        # ── Buttons ───────────────────────────────────────────────────────── #
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        root.addWidget(btn_box)

        self._set_editor_enabled(False)

    # ── Helpers ─────────────────────────────────────────────────────────────── #

    def _refresh_list(self) -> None:
        self._list.blockSignals(True)
        self._list.clear()
        for tpl in self.library:
            item = QListWidgetItem(tpl.name)
            item.setData(Qt.ItemDataRole.UserRole, str(tpl.id))
            self._list.addItem(item)
        self._list.blockSignals(False)
        has = bool(self.library)
        self._empty_label.setVisible(not has)
        self._set_editor_enabled(has)
        if has:
            self._list.setCurrentRow(0)

    def _set_editor_enabled(self, enabled: bool) -> None:
        for w in (self._name_edit, self._desc_edit, self._html_edit):
            w.setEnabled(enabled)

    def _load_template(self, tpl: ExtensionTemplate) -> None:
        self._name_edit.blockSignals(True)
        self._desc_edit.blockSignals(True)
        self._html_edit.blockSignals(True)
        self._name_edit.setText(tpl.name)
        self._desc_edit.setText(tpl.description)
        self._html_edit.setPlainText(tpl.html)
        self._name_edit.blockSignals(False)
        self._desc_edit.blockSignals(False)
        self._html_edit.blockSignals(False)

    # ── Slots ────────────────────────────────────────────────────────────────── #

    def _on_row_changed(self, row: int) -> None:
        self._current_idx = row
        if 0 <= row < len(self.library):
            self._load_template(self.library[row])
            self._set_editor_enabled(True)
        else:
            self._set_editor_enabled(False)

    def _on_name_changed(self, text: str) -> None:
        if 0 <= self._current_idx < len(self.library):
            self.library[self._current_idx].name = text
            item = self._list.item(self._current_idx)
            if item:
                item.setText(text)

    def _on_desc_changed(self, text: str) -> None:
        if 0 <= self._current_idx < len(self.library):
            self.library[self._current_idx].description = text

    def _on_html_changed(self) -> None:
        if 0 <= self._current_idx < len(self.library):
            self.library[self._current_idx].html = self._html_edit.toPlainText()

    def _new_extension(self) -> None:
        from bimap.ui.dialogs.extension_editor_dialog import _TEMPLATE_HELLO_WORLD
        tpl = ExtensionTemplate(name=t("New Extension"), html=_TEMPLATE_HELLO_WORLD)
        self.library.append(tpl)
        item = QListWidgetItem(tpl.name)
        item.setData(Qt.ItemDataRole.UserRole, str(tpl.id))
        self._list.addItem(item)
        self._list.setCurrentRow(len(self.library) - 1)
        self._empty_label.setVisible(False)
        self._set_editor_enabled(True)
        self._name_edit.setFocus()
        self._name_edit.selectAll()

    def _delete_extension(self) -> None:
        row = self._current_idx
        if row < 0 or row >= len(self.library):
            return
        name = self.library[row].name
        msg = t("Confirm Delete")
        body = t("Delete extension '{name}'? This cannot be undone.").replace(
            "{name}", name
        )
        reply = QMessageBox.question(
            self, msg, body,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        del self.library[row]
        self._list.takeItem(row)
        self._current_idx = -1
        if self.library:
            new_row = min(row, len(self.library) - 1)
            self._list.setCurrentRow(new_row)
        else:
            self._empty_label.setVisible(True)
            self._set_editor_enabled(False)
