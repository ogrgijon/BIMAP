"""
BIMAP application entry point.

Usage
-----
    python -m bimap.app          # run directly
    bimap                        # if installed via pip/pyproject.toml entry-point
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QIcon, QPixmap
from PyQt6.QtWidgets import QApplication, QSplashScreen

from bimap.config import APP_NAME, APP_ORGANISATION, APP_VERSION, THEME_QSS_PATH

# Suppress Qt font-directory warnings (harmless on systems without certain fonts)
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.fonts=false")

# Assets live at the project root (two levels above src/bimap/)
_ROOT = Path(__file__).parent.parent.parent


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_ORGANISATION)
    app.setApplicationVersion(APP_VERSION)
    app.setStyle("Fusion")
    # Apply VS Code dark theme unless --no-theme is passed
    if "--no-theme" not in sys.argv and THEME_QSS_PATH.exists():
        app.setStyleSheet(THEME_QSS_PATH.read_text(encoding="utf-8"))
    # High-DPI scaling is automatic in Qt 6.x — AA_UseHighDpiPixmaps was removed in Qt 6.7

    # App icon
    _ico = _ROOT / "bimap.ico"
    if _ico.exists():
        app.setWindowIcon(QIcon(str(_ico)))

    # Splash screen — shown before the heavy MainWindow import
    splash: QSplashScreen | None = None
    _splash_png = _ROOT / "bimap_splash.png"
    if _splash_png.exists():
        splash = QSplashScreen(QPixmap(str(_splash_png)))
        splash.show()
        splash.showMessage(
            f"Loading {APP_NAME}…",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
            QColor("#FFFFFF"),
        )
        app.processEvents()

    # Lazy import to keep startup fast and allow QApplication to exist first
    from bimap.ui.main_window import MainWindow

    window = MainWindow()
    window.show()
    if splash is not None:
        splash.finish(window)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
