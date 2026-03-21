# ============================================================================
# BIMAP Installer Builder — Windows
# ============================================================================
# Prerequisites:
#   1. Python 3.11+ with the project venv at .\.venv\
#   2. PyInstaller (auto-installed below)
#   3. Inno Setup 6 at C:\Program Files (x86)\Inno Setup 6\ISCC.exe
#      Download: https://jrsoftware.org/isdl.php
# ============================================================================

param (
    [string]$Version = "0.1.0",
    [switch]$SkipPyInstaller,
    [switch]$SkipInnoSetup
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$Dist  = Join-Path $Root "installer\dist"
$Build = Join-Path $Root "installer\build"

Write-Host "=== BIMAP Installer Builder v$Version ===" -ForegroundColor Cyan

# ── 1. Activate venv ────────────────────────────────────────────────────────
$Activate = Join-Path $Root ".venv\Scripts\Activate.ps1"
if (Test-Path $Activate) {
    . $Activate
    Write-Host "  [OK] Virtual env activated" -ForegroundColor Green
} else {
    Write-Error "Virtual env not found at .venv\. Run: python -m venv .venv && .venv\Scripts\pip install -r requirements.txt"
}

# ── 2. Install PyInstaller if needed ────────────────────────────────────────
if (-not $SkipPyInstaller) {
    Write-Host "  [..] Installing/upgrading PyInstaller..." -ForegroundColor Yellow
    pip install --quiet --upgrade pyinstaller pyinstaller-hooks-contrib
    Write-Host "  [OK] PyInstaller ready" -ForegroundColor Green
}

# ── 3. Run PyInstaller ───────────────────────────────────────────────────────
if (-not $SkipPyInstaller) {
    Write-Host "  [..] Running PyInstaller..." -ForegroundColor Yellow

    $SpecFile = Join-Path $Root "installer\bimap.spec"

    if (Test-Path $SpecFile) {
        pyinstaller $SpecFile `
            --distpath $Dist `
            --workpath $Build `
            --noconfirm
    } else {
        # Generate spec on first run
        pyinstaller `
            (Join-Path $Root "src\bimap\app.py") `
            --name "BIMAP" `
            --onedir `
            --windowed `
            --icon (Join-Path $Root "installer\bimap.ico") `
            --distpath $Dist `
            --workpath $Build `
            --noconfirm `
            --add-data (Join-Path $Root "readme.md" + ";.") `
            --paths (Join-Path $Root "src") `
            --hidden-import PyQt6.QtSvg `
            --hidden-import PyQt6.QtPrintSupport `
            --hidden-import diskcache `
            --hidden-import geopy `
            --hidden-import reportlab `
            --hidden-import pydantic `
            --hidden-import openpyxl `
            --hidden-import sqlalchemy
    }

    Write-Host "  [OK] PyInstaller build complete -> $Dist\BIMAP\" -ForegroundColor Green
}

# ── 4. Run Inno Setup ────────────────────────────────────────────────────────
if (-not $SkipInnoSetup) {
    $ISCC = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    $IssFile = Join-Path $Root "installer\bimap_setup.iss"

    if (-not (Test-Path $ISCC)) {
        Write-Warning "Inno Setup not found at '$ISCC'. Skipping installer packaging."
        Write-Warning "Download from: https://jrsoftware.org/isdl.php"
    } elseif (-not (Test-Path $IssFile)) {
        Write-Warning "bimap_setup.iss not found. Skipping Inno Setup step."
    } else {
        Write-Host "  [..] Building Windows installer with Inno Setup..." -ForegroundColor Yellow
        & $ISCC $IssFile /DMyAppVersion=$Version
        Write-Host "  [OK] Installer created in installer\output\" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "=== Build complete ===" -ForegroundColor Cyan
Write-Host "  Standalone app : $Dist\BIMAP\BIMAP.exe"
Write-Host "  Installer      : $Root\installer\output\BIMAP_Setup_$Version.exe"
