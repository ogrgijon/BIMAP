"""HTML5/CSS/JS Extension Editor and Viewer dialog.

Users can write an HTML5 document (with embedded CSS and JS) that will be
rendered in the system browser with the element's data injected as the
``BIMAP_DATA`` JavaScript object.

BIMAP_DATA structure injected at runtime
-----------------------------------------
    {
        "type":     "zone" | "keypoint",
        "id":       "<uuid>",
        "name":     "<element name>",
        "group":    "<group>",
        "layer":    "<layer>",
        "metadata": { "key": "value", ... },
        // Keypoints only:
        "info_card": {
            "title":    "...",
            "subtitle": "...",
            "notes":    "...",
            "link_url": "...",
            "fields":   [{"label": "...", "value": "..."}, ...]
        }
    }
"""

from __future__ import annotations

import json
import tempfile
import webbrowser
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from bimap.i18n import t

# ── Chart.js bundled asset path ──────────────────────────────────────────────
# chart.min.js is stored alongside the package data for offline use.
# The extension viewer sets a base URL pointing to this directory so that
# templates referencing "chart.min.js" as a relative path load correctly.
_CHARTJS_CDN_URL = "https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"
_CHARTJS_LOCAL_SRC = "chart.min.js"   # resolved relative to bimap/data/ at runtime


def _chartjs_script_tag() -> str:
    """Return the <script> tag to load Chart.js — local copy when available, CDN fallback."""
    import importlib.resources
    try:
        # Python 3.9+: files() returns a Traversable
        pkg_data = importlib.resources.files("bimap.data")
        js_path = pkg_data.joinpath(_CHARTJS_LOCAL_SRC)
        if js_path.is_file():
            return f'<script src="{_CHARTJS_LOCAL_SRC}"></script>'
    except Exception:
        pass
    return f'<script src="{_CHARTJS_CDN_URL}"></script>'


# ── Built-in starter templates ───────────────────────────────────────────────

_TEMPLATE_TABLE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>BIMAP Extension</title>
<style>
  body { font-family: sans-serif; background: #1e1e2e; color: #cdd6f4; margin: 0; padding: 16px; }
  h2   { color: #89dceb; margin-bottom: 8px; }
  table{ border-collapse: collapse; width: 100%; }
  th   { background: #313244; color: #cba6f7; text-align: left; padding: 6px 10px; }
  td   { padding: 6px 10px; border-bottom: 1px solid #45475a; }
</style>
</head>
<body>
<h2 id="title"></h2>
<table>
  <thead><tr><th>Key</th><th>Value</th></tr></thead>
  <tbody id="rows"></tbody>
</table>
<script>
  const el = BIMAP_DATA;
  document.getElementById('title').textContent = el.name + ' — ' + el.type;
  const tbody = document.getElementById('rows');
  Object.entries(el.metadata).forEach(([k, v]) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${k}</td><td>${v}</td>`;
    tbody.appendChild(tr);
  });
</script>
</body>
</html>
"""

_TEMPLATE_BAR = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>BIMAP Extension</title>
<style>
  body   { font-family: sans-serif; background: #1e1e2e; color: #cdd6f4; margin: 0; padding: 16px; }
  h2     { color: #89dceb; }
  .bar-wrap { display: flex; flex-direction: column; gap: 8px; margin-top: 12px; }
  .bar-row  { display: flex; align-items: center; gap: 8px; }
  .bar-label{ width: 140px; font-size: 12px; text-align: right; }
  .bar-bg   { flex: 1; background: #313244; border-radius: 4px; height: 22px; overflow: hidden; }
  .bar-fill { height: 100%; background: #89b4fa; border-radius: 4px;
              display: flex; align-items: center; padding-left: 6px;
              font-size: 11px; white-space: nowrap; transition: width 0.4s; }
</style>
</head>
<body>
<h2 id="title"></h2>
<div class="bar-wrap" id="bars"></div>
<script>
  const el = BIMAP_DATA;
  document.getElementById('title').textContent = el.name;
  const container = document.getElementById('bars');
  const numericEntries = Object.entries(el.metadata)
    .map(([k, v]) => [k, parseFloat(v)])
    .filter(([, v]) => !isNaN(v));
  const max = Math.max(...numericEntries.map(([, v]) => v), 1);
  numericEntries.forEach(([k, v]) => {
    const pct = (v / max * 100).toFixed(1);
    container.innerHTML += `
      <div class="bar-row">
        <div class="bar-label">${k}</div>
        <div class="bar-bg">
          <div class="bar-fill" style="width:${pct}%">${v}</div>
        </div>
      </div>`;
  });
</script>
</body>
</html>
"""

_TEMPLATE_GAUGE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>BIMAP Extension</title>
<style>
  body   { font-family: sans-serif; background: #1e1e2e; color: #cdd6f4; margin: 0;
           display: flex; flex-direction: column; align-items: center; padding: 24px; }
  h2     { color: #89dceb; margin-bottom: 4px; }
  .gauge { position: relative; width: 200px; height: 100px; overflow: hidden; margin: 16px 0; }
  .gauge svg { width: 100%; height: 100%; }
  .value { font-size: 2em; font-weight: bold; color: #a6e3a1; }
  .label { font-size: 0.85em; color: #9399b2; }
</style>
</head>
<body>
<h2 id="name"></h2>
<div class="gauge">
  <svg viewBox="0 0 200 100">
    <path d="M10,100 A90,90 0 0,1 190,100" fill="none" stroke="#313244" stroke-width="18"/>
    <path id="arc" d="M10,100 A90,90 0 0,1 190,100" fill="none"
          stroke="#89b4fa" stroke-width="18" stroke-dasharray="283" stroke-dashoffset="283"/>
  </svg>
</div>
<div class="value" id="val">—</div>
<div class="label" id="key">first numeric metadata key</div>
<script>
  const el = BIMAP_DATA;
  document.getElementById('name').textContent = el.name;
  const entry = Object.entries(el.metadata)
    .map(([k, v]) => [k, parseFloat(v)])
    .find(([, v]) => !isNaN(v));
  if (entry) {
    const [k, v] = entry;
    document.getElementById('val').textContent = v;
    document.getElementById('key').textContent = k;
    // Assume 0-100 range; clamp
    const pct = Math.min(Math.max(v, 0), 100) / 100;
    document.getElementById('arc').style.strokeDashoffset = (283 * (1 - pct)).toFixed(1);
  }
</script>
</body>
</html>
"""

_TEMPLATE_LINE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>BIMAP Extension</title>
<style>
  body { font-family: sans-serif; background: #1e1e2e; color: #cdd6f4; margin: 0; padding: 16px; }
  h2   { color: #89dceb; margin-bottom: 12px; }
  .chart-wrap { position: relative; height: 240px; }
</style>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
</head>
<body>
<h2 id="title"></h2>
<div class="chart-wrap"><canvas id="chart"></canvas></div>
<script>
  const el = BIMAP_DATA;
  document.getElementById('title').textContent = el.name;
  const entries = Object.entries(el.metadata)
    .map(([k, v]) => [k, parseFloat(v)])
    .filter(([, v]) => !isNaN(v));
  new Chart(document.getElementById('chart'), {
    type: 'line',
    data: {
      labels: entries.map(([k]) => k),
      datasets: [{
        label: el.name,
        data: entries.map(([, v]) => v),
        borderColor: '#89b4fa',
        backgroundColor: 'rgba(137,180,250,0.15)',
        pointBackgroundColor: '#cba6f7',
        tension: 0.35,
        fill: true
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#cdd6f4' } } },
      scales: {
        x: { ticks: { color: '#9399b2' }, grid: { color: '#313244' } },
        y: { ticks: { color: '#9399b2' }, grid: { color: '#313244' } }
      }
    }
  });
</script>
</body>
</html>
"""

_TEMPLATE_PIE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>BIMAP Extension</title>
<style>
  body { font-family: sans-serif; background: #1e1e2e; color: #cdd6f4; margin: 0; padding: 16px; }
  h2   { color: #89dceb; margin-bottom: 12px; }
  .chart-wrap { position: relative; height: 260px; }
</style>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
</head>
<body>
<h2 id="title"></h2>
<div class="chart-wrap"><canvas id="chart"></canvas></div>
<script>
  const el = BIMAP_DATA;
  document.getElementById('title').textContent = el.name;
  const entries = Object.entries(el.metadata)
    .map(([k, v]) => [k, parseFloat(v)])
    .filter(([, v]) => !isNaN(v));
  const palette = ['#89b4fa','#a6e3a1','#fab387','#f38ba8','#cba6f7','#94e2d5','#f9e2af','#89dceb'];
  new Chart(document.getElementById('chart'), {
    type: 'doughnut',
    data: {
      labels: entries.map(([k]) => k),
      datasets: [{
        data: entries.map(([, v]) => v),
        backgroundColor: palette,
        borderColor: '#1e1e2e',
        borderWidth: 2
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { position: 'right', labels: { color: '#cdd6f4', boxWidth: 14 } }
      }
    }
  });
</script>
</body>
</html>
"""

_TEMPLATE_RADAR = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>BIMAP Extension</title>
<style>
  body { font-family: sans-serif; background: #1e1e2e; color: #cdd6f4; margin: 0; padding: 16px; }
  h2   { color: #89dceb; margin-bottom: 12px; }
  .chart-wrap { position: relative; height: 260px; }
</style>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
</head>
<body>
<h2 id="title"></h2>
<div class="chart-wrap"><canvas id="chart"></canvas></div>
<script>
  const el = BIMAP_DATA;
  document.getElementById('title').textContent = el.name;
  const entries = Object.entries(el.metadata)
    .map(([k, v]) => [k, parseFloat(v)])
    .filter(([, v]) => !isNaN(v));
  new Chart(document.getElementById('chart'), {
    type: 'radar',
    data: {
      labels: entries.map(([k]) => k),
      datasets: [{
        label: el.name,
        data: entries.map(([, v]) => v),
        borderColor: '#a6e3a1',
        backgroundColor: 'rgba(166,227,161,0.2)',
        pointBackgroundColor: '#f9e2af',
        pointRadius: 4
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#cdd6f4' } } },
      scales: {
        r: {
          ticks: { color: '#9399b2', backdropColor: 'transparent' },
          grid: { color: '#313244' },
          pointLabels: { color: '#cdd6f4' }
        }
      }
    }
  });
</script>
</body>
</html>
"""

_TEMPLATE_HELLO_WORLD = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {
    margin: 0;
    background: #1e1e2e;
    color: #cdd6f4;
    font-family: Arial, sans-serif;
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100vh;
  }
  .card {
    background: #313244;
    border-radius: 12px;
    padding: 2rem;
    max-width: 400px;
    text-align: center;
    box-shadow: 0 4px 24px #0006;
  }
  h1 { color: #cba6f7; margin-bottom: 0.5rem; }
  .type { font-size: 0.8rem; letter-spacing: 0.1em; color: #89b4fa; text-transform: uppercase; }
  .meta { font-size: 0.9rem; color: #a6adc8; margin-top: 1rem; }
</style>
</head>
<body>
<script>
// BIMAP_DATA is injected at runtime — this placeholder is for editor preview
const BIMAP_DATA = window.BIMAP_DATA || {
  name: "My Element",
  type: "zone",
  metadata: { Example: "value" }
};
</script>
<div class="card">
  <div class="type" id="etype"></div>
  <h1 id="title"></h1>
  <div class="meta" id="meta"></div>
</div>
<script>
  document.getElementById("etype").textContent = BIMAP_DATA.type || "";
  document.getElementById("title").textContent = BIMAP_DATA.name || "Hello World";
  const meta = BIMAP_DATA.metadata || {};
  const keys = Object.keys(meta);
  document.getElementById("meta").textContent =
    keys.length ? keys.map(k => k + ": " + meta[k]).join(" · ") : "No metadata yet.";
</script>
</body>
</html>
"""

_TEMPLATES: dict[str, str] = {
    "Hello World (starter)": _TEMPLATE_HELLO_WORLD,
    "Table (all metadata)": _TEMPLATE_TABLE,
    "Bar Chart (metadata values)": _TEMPLATE_BAR,
    "Gauge (single value)": _TEMPLATE_GAUGE,
    "Line Chart (Chart.js)": _TEMPLATE_LINE,
    "Donut Chart (Chart.js)": _TEMPLATE_PIE,
    "Radar Chart (Chart.js)": _TEMPLATE_RADAR,
}

# Replace CDN Chart.js URL with the appropriate local/CDN script tag in Chart templates
_CHARTJS_SCRIPT_TAG = _chartjs_script_tag()
_CDN_SCRIPT_TAG = f'<script src="{_CHARTJS_CDN_URL}"></script>'
_TEMPLATES = {
    name: html.replace(_CDN_SCRIPT_TAG, _CHARTJS_SCRIPT_TAG)
    for name, html in _TEMPLATES.items()
}


def _build_data_payload(element: Any, etype: str) -> dict:
    """Build the BIMAP_DATA dict to inject into the HTML extension."""
    payload: dict = {
        "type": etype,
        "id": str(element.id),
        "name": getattr(element, "name", ""),
        "group": getattr(element, "group", ""),
        "layer": getattr(element, "layer", ""),
        "metadata": {
            k: v for k, v in getattr(element, "metadata", {}).items()
            if k not in getattr(element, "metadata_hidden", [])
        },
    }
    if etype == "keypoint":
        ic = getattr(element, "info_card", None)
        if ic:
            payload["info_card"] = {
                "title": ic.title,
                "subtitle": ic.subtitle,
                "notes": ic.notes,
                "link_url": ic.link_url,
                "fields": [{"label": f.label, "value": f.value} for f in ic.fields],
            }
    return payload


def launch_extension_in_browser(element: Any, etype: str) -> None:
    """Inject BIMAP_DATA into the element's extension_html and open in the
    system default browser via a temporary file.

    Raises ``ValueError`` if the element has no extension_html set.
    """
    html_template: str = getattr(element, "extension_html", "").strip()
    if not html_template:
        raise ValueError("No extension configured for this element.")

    payload = _build_data_payload(element, etype)
    data_js = json.dumps(payload, ensure_ascii=False, indent=2)
    injection = f"<script>\nconst BIMAP_DATA = {data_js};\n</script>\n"

    # Inject the data block right before </head> or if not found, at the top.
    if "</head>" in html_template:
        rendered = html_template.replace("</head>", injection + "</head>", 1)
    else:
        rendered = injection + html_template

    tmp = tempfile.NamedTemporaryFile(
        suffix=".html", mode="w", encoding="utf-8", delete=False
    )
    tmp.write(rendered)
    tmp.close()
    webbrowser.open(Path(tmp.name).as_uri())


class ExtensionEditorDialog(QDialog):
    """Full-screen HTML5/CSS/JS editor for a single element's extension.

    After ``exec()`` returns ``Accepted``, read ``html_result`` to get the
    saved HTML template (empty str means "clear the extension").
    """

    def __init__(
        self,
        element: Any,
        etype: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._element = element
        self._etype = etype
        name = getattr(element, "name", str(getattr(element, "id", "")))
        self.setWindowTitle(
            t("Extension Editor") + f" — {name}"
        )
        self.resize(800, 640)
        self.html_result: str = getattr(element, "extension_html", "")
        self._setup_ui()
        self._show_onboarding()

    def _show_onboarding(self) -> None:
        """Show a first-use explanation of BIMAP extensions (once per install)."""
        s = QSettings("BIMAP", "BIMAP")
        if s.value("extension_editor_intro_shown", False, type=bool):
            return
        s.setValue("extension_editor_intro_shown", True)
        QMessageBox.information(
            self,
            "BIMAP Extensions",
            "<b>BIMAP Extensions</b> are HTML5 pages embedded in a zone or keypoint.<br><br>"
            "At runtime they receive a <code>BIMAP_DATA</code> JavaScript object containing:<br>"
            "&nbsp;&bull;&nbsp;<b>type</b> — <i>'zone'</i> or <i>'keypoint'</i><br>"
            "&nbsp;&bull;&nbsp;<b>name</b> — element name<br>"
            "&nbsp;&bull;&nbsp;<b>metadata</b> — dict of key→value pairs you defined<br>"
            "&nbsp;&bull;&nbsp;<b>info_card</b> — title, body, tags (keypoints only)<br><br>"
            "Use the <i>Load Template</i> dropdown to start from a built-in example, or "
            "<i>From Library…</i> to import a saved template from your extension library.",
        )

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(8)

        # ── Header / template loader ──────────────────────────────────────── #
        top_row = QHBoxLayout()
        hint = QLabel(
            "Write an HTML5 document. "
            "<code>BIMAP_DATA</code> is injected as a JS variable with element "
            "data (name, type, metadata, info_card for keypoints)."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #858585; font-size: 11px;")
        top_row.addWidget(hint, 1)

        tpl_combo = QComboBox()
        tpl_combo.addItem(t("Load Template"))
        for name in _TEMPLATES:
            tpl_combo.addItem(t(name))
        tpl_combo.currentTextChanged.connect(self._on_template_selected)
        top_row.addWidget(tpl_combo)

        btn_from_lib = QPushButton(t("From Library\u2026"))
        btn_from_lib.setToolTip("Import HTML from a saved extension library template")
        btn_from_lib.clicked.connect(self._from_library)
        top_row.addWidget(btn_from_lib)

        root.addLayout(top_row)

        # ── Code editor ───────────────────────────────────────────────────── #
        self._editor = QPlainTextEdit()
        self._editor.setPlainText(self.html_result)
        mono = QFont("Consolas", 10)
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self._editor.setFont(mono)
        self._editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._editor.setStyleSheet(
            "background: #1e1e1e; color: #d4d4d4;"
            "border: 1px solid #3C3C3C;"
        )
        self._editor.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        root.addWidget(self._editor, 1)

        # ── Bottom bar ────────────────────────────────────────────────────── #
        btn_row = QHBoxLayout()
        btn_preview = QPushButton(t("Open in Browser"))
        btn_preview.setToolTip("Inject current data and open in the system browser")
        btn_preview.clicked.connect(self._preview)
        btn_row.addWidget(btn_preview)
        btn_row.addStretch()

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self._on_save)
        btn_box.rejected.connect(self.reject)
        btn_row.addWidget(btn_box)
        root.addLayout(btn_row)

    # ── Slots ──────────────────────────────────────────────────────────────── #

    def _from_library(self) -> None:
        """Show a picker to load HTML from the project extension library."""
        library = []
        # Traverse up to find a parent widget that has _project (main window)
        w = self.parent()
        while w is not None:
            library = getattr(getattr(w, "_project", None), "extension_library", [])
            if library:
                break
            w = w.parent() if hasattr(w, "parent") else None
        if not library:
            QMessageBox.information(
                self,
                t("Extension Library"),
                "No templates saved in the extension library yet.\n"
                "Use Data \u2192 Manage Extensions\u2026 to create library entries.",
            )
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(t("Choose from Library"))
        dlg.resize(420, 300)
        vl = QVBoxLayout(dlg)
        vl.addWidget(QLabel(t("Select a template to load into the editor:")))
        lst = QListWidget()
        for tpl in library:
            lst.addItem(tpl.name)
        vl.addWidget(lst)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        vl.addWidget(btns)
        if dlg.exec() and lst.currentRow() >= 0:
            tpl = library[lst.currentRow()]
            if not self._editor.toPlainText().strip() or QMessageBox.question(
                self,
                t("Load Template"),
                "Replace current content with the selected template?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            ) == QMessageBox.StandardButton.Yes:
                self._editor.setPlainText(tpl.html)

    def _on_template_selected(self, text: str) -> None:
        key = text
        # Reverse-translate if in ES
        for en_key, tpl in _TEMPLATES.items():
            if t(en_key) == text or en_key == text:
                if not self._editor.toPlainText().strip() or QMessageBox.question(
                    self,
                    "Load Template",
                    "Replace current content with the selected template?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                ) == QMessageBox.StandardButton.Yes:
                    self._editor.setPlainText(tpl)
                break

    def _preview(self) -> None:
        html = self._editor.toPlainText().strip()
        if not html:
            QMessageBox.warning(self, "Preview", t("HTML content is required."))
            return
        payload = _build_data_payload(self._element, self._etype)
        data_js = __import__("json").dumps(payload, ensure_ascii=False, indent=2)
        injection = f"<script>\nconst BIMAP_DATA = {data_js};\n</script>\n"
        if "</head>" in html:
            rendered = html.replace("</head>", injection + "</head>", 1)
        else:
            rendered = injection + html
        import tempfile
        tmp = tempfile.NamedTemporaryFile(
            suffix=".html", mode="w", encoding="utf-8", delete=False
        )
        tmp.write(rendered)
        tmp.close()
        import webbrowser
        from pathlib import Path
        webbrowser.open(Path(tmp.name).as_uri())

    def _on_save(self) -> None:
        self.html_result = self._editor.toPlainText().strip()
        self.accept()
