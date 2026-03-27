@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%~dp0app"

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found. Please install Python 3 first.
    pause
    exit /b 1
)

python -c "import pikpakapi, PySide6" >nul 2>nul
if errorlevel 1 (
    echo Installing dependencies...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
)

echo Starting desktop client...
python "%~dp0scripts\run_gui.py"
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to start the desktop client.
    pause
    exit /b 1
)
