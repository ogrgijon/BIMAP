"""Add / Edit data source dialog."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from bimap.models.data_source import DataSource, RefreshMode, SourceType
from bimap.i18n import t


class DataSourceDialog(QDialog):
    """Dialog to create or edit a DataSource model."""

    def __init__(self, source: DataSource | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._source: DataSource = source or DataSource()
        self.setWindowTitle(t("Data Source") if source else t("Add Data Source"))
        self.setMinimumWidth(440)
        self._setup_ui()
        if source:
            self._load(source)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)

        form = QFormLayout()
        self._name_edit = QLineEdit()
        form.addRow(t("Name"), self._name_edit)

        self._type_combo = QComboBox()
        for st in SourceType:
            if st == SourceType.GOOGLE_SHEETS:
                continue
            self._type_combo.addItem(st.value, st)
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        form.addRow(t("Type"), self._type_combo)
        root.addLayout(form)

        # Stacked pages per source type
        self._stack = QStackedWidget()
        self._pages: dict[str, QWidget] = {}
        for st in SourceType:
            page = self._build_page(st)
            self._pages[st.value] = page
            self._stack.addWidget(page)
        root.addWidget(self._stack)

        # Refresh settings
        refresh_grp = QGroupBox(t("Refresh"))
        refresh_form = QFormLayout(refresh_grp)
        self._refresh_combo = QComboBox()
        for rm in RefreshMode:
            self._refresh_combo.addItem(rm.value, rm)
        refresh_form.addRow(t("Mode"), self._refresh_combo)
        self._interval_spin = QSpinBox()
        self._interval_spin.setRange(30, 86400)
        self._interval_spin.setSuffix(" sec")
        self._interval_spin.setValue(300)
        refresh_form.addRow(t("Interval"), self._interval_spin)
        root.addWidget(refresh_grp)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._on_type_changed(0)

    def _build_page(self, st: SourceType) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        match st:
            case SourceType.CSV | SourceType.EXCEL:
                path_widget = QWidget()
                row = QHBoxLayout(path_widget)
                row.setContentsMargins(0, 0, 0, 0)
                edit = QLineEdit()
                edit.setObjectName("file_path")
                btn = QPushButton("Browse…")
                btn.clicked.connect(lambda: self._browse_file(edit))
                row.addWidget(edit)
                row.addWidget(btn)
                form.addRow("File Path", path_widget)
                sheet = QLineEdit()
                sheet.setObjectName("sheet_name")
                sheet.setPlaceholderText("Sheet name or index (default: 0)")
                form.addRow("Sheet", sheet)

            case SourceType.SQL:
                conn_edit = QLineEdit()
                conn_edit.setObjectName("connection_string")
                conn_edit.setPlaceholderText("e.g. postgresql://user:pass@host/db")
                form.addRow("Connection", conn_edit)
                query_edit = QLineEdit()
                query_edit.setObjectName("query")
                query_edit.setPlaceholderText("SELECT * FROM table")
                form.addRow("Query", query_edit)

            case SourceType.REST_API:
                url_edit = QLineEdit()
                url_edit.setObjectName("url")
                url_edit.setPlaceholderText("https://api.example.com/data")
                form.addRow("URL", url_edit)
                path_edit = QLineEdit()
                path_edit.setObjectName("data_path")
                path_edit.setPlaceholderText("e.g. results.items  (leave empty for root)")
                form.addRow("Data Path", path_edit)
                token_edit = QLineEdit()
                token_edit.setObjectName("auth_token")
                token_edit.setEchoMode(QLineEdit.EchoMode.Password)
                form.addRow("Auth Token", token_edit)

            case SourceType.GEOJSON:
                src_widget = QWidget()
                row = QHBoxLayout(src_widget)
                row.setContentsMargins(0, 0, 0, 0)
                edit = QLineEdit()
                edit.setObjectName("path_or_url")
                edit.setPlaceholderText("Local path or https://…")
                btn = QPushButton("Browse…")
                btn.clicked.connect(lambda: self._browse_file(edit))
                row.addWidget(edit)
                row.addWidget(btn)
                form.addRow("Source", src_widget)

            case _:
                form.addRow(QLabel(f"Source type '{st}' not yet configurable in UI."))
        return page

    def _browse_file(self, edit: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "All Files (*.*)")
        if path:
            edit.setText(path)

    def _on_type_changed(self, _index: int) -> None:
        st = self._type_combo.currentData()
        if st:
            page = self._pages.get(st.value)
            if page:
                self._stack.setCurrentWidget(page)

    def _load(self, source: DataSource) -> None:
        self._name_edit.setText(source.name)
        idx = self._type_combo.findData(source.source_type)
        if idx >= 0:
            self._type_combo.setCurrentIndex(idx)
        rm_idx = self._refresh_combo.findData(source.refresh_mode)
        if rm_idx >= 0:
            self._refresh_combo.setCurrentIndex(rm_idx)
        self._interval_spin.setValue(source.refresh_interval_sec)
        # Populate page fields from connection dict
        page = self._pages.get(source.source_type.value)
        if page:
            conn = dict(source.connection)
            # Restore SQL connection_string from keychain for editing
            if source.source_type.value == "sql" and "connection_string" not in conn:
                from bimap.secrets import get_secret
                stored = get_secret(f"datasource_{str(source.id)}")
                if stored:
                    conn["connection_string"] = stored
            for key, val in conn.items():
                edit = page.findChild(QLineEdit, key)
                if edit:
                    edit.setText(str(val))

    def _on_accept(self) -> None:
        self._source.name = self._name_edit.text().strip() or "Data Source"
        self._source.source_type = self._type_combo.currentData()
        self._source.refresh_mode = self._refresh_combo.currentData()
        self._source.refresh_interval_sec = self._interval_spin.value()
        # Gather connection params from current page
        page = self._pages.get(self._source.source_type.value)
        if page:
            conn: dict[str, str] = {}
            for edit in page.findChildren(QLineEdit):
                if edit.objectName():
                    conn[edit.objectName()] = edit.text()
            self._source.connection = conn
        # Move SQL connection_string to OS keychain so it is not saved in the project file
        if self._source.source_type.value == "sql":
            conn_str = self._source.connection.pop("connection_string", "") or ""
            if conn_str:
                from bimap.secrets import set_secret
                set_secret(f"datasource_{str(self._source.id)}", conn_str)
        self.accept()

    @property
    def source(self) -> DataSource:
        return self._source
