@echo off
setlocal enabledelayedexpansion
title Building SnapMerge
color 0A

REM --- venv ---
if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual env...
    py -m venv .venv
)
call .venv\Scripts\activate.bat
set PYTHONPATH=%CD%\src

REM --- deps ---
python -m pip install --upgrade pip >nul
python -m pip install -U -r requirements.txt pyinstaller >nul

REM --- write build info (version basado en git/CI) ---
python src\snapmerge\app_version\write_build_info.py

REM --- clean ---
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist SnapMerge.spec del SnapMerge.spec

REM *** IMPORTANT: this line generates common\build_info.py before building ***
python src\snapmerge\app_version\write_build_info.py
set "VER=src\snapmerge\app_version\version_info.txt"

REM *** Generate version_info.txt (from build_info) ***
python src\snapmerge\app_version\write_version_info.py 

if not exist "%VER%"  echo [ERROR] Missing %VER% & exit /b 1

REM --- build ---
pyinstaller --noconfirm --onefile --windowed --name SnapMerge --version-file "%VER%" ^
  --icon "src\snapmerge\ui\sm-icon.ico" ^
  --add-data "config.yaml;." ^
  --add-data "src\snapmerge\ui\sm-icon.ico;snapmerge/ui" ^
  --collect-all Crypto ^
  --hidden-import PySide6 ^
  --hidden-import PySide6.QtWidgets ^
  --hidden-import PySide6.QtGui ^
  --hidden-import PySide6.QtCore ^
  --hidden-import shiboken6 ^
  --exclude-module PyQt5 ^
  --exclude-module PyQt6 ^
  -p src main.py

echo.
echo ============================================
echo  Build completed: dist\SnapMerge.exe
echo ============================================
pause