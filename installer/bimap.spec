"""
PyInstaller spec file for BIMAP.

Generate once with:
    pyinstaller installer/bimap.spec

Or use build_installer.ps1 which handles the full pipeline.
"""

import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent          # noqa: F821 — SPECPATH is injected by PyInstaller
SRC  = str(ROOT / "src")

block_cipher = None

a = Analysis(
    [str(ROOT / "src" / "bimap" / "app.py")],
    pathex=[SRC],
    binaries=[],
    datas=[
        (str(ROOT / "readme.md"), "."),
    ],
    hiddenimports=[
        # PyQt6 plugins that auto-discovery may miss
        "PyQt6.QtSvg",
        "PyQt6.QtPrintSupport",
        "PyQt6.QtNetwork",
        # Data / storage
        "diskcache",
        "geopy",
        "geopy.geocoders",
        # PDF
        "reportlab",
        "reportlab.lib",
        "reportlab.platypus",
        "reportlab.graphics",
        # Data sources
        "openpyxl",
        "sqlalchemy",
        "sqlalchemy.dialects",
        "sqlalchemy.pool",
        "httpx",
        "keyring",
        "keyring.backends",
        # Pydantic
        "pydantic",
        "pydantic.v1",
        "pydantic_core",
        # Standard
        "csv",
        "json",
        "uuid",
        "pathlib",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "IPython",
        "jupyter",
        "notebook",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)  # noqa: F821

exe = EXE(                                              # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BIMAP",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "installer" / "bimap.ico") if (ROOT / "installer" / "bimap.ico").exists() else None,
    version=str(ROOT / "installer" / "file_version_info.txt") if (ROOT / "installer" / "file_version_info.txt").exists() else None,
)

coll = COLLECT(                                         # noqa: F821
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="BIMAP",
)
