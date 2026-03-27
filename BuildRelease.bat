@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found.
    pause
    exit /b 1
)

echo Building onedir app and installer...
python "%~dp0packaging\build_release.py"
if errorlevel 1 (
    echo.
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

echo.
echo Build completed successfully.
echo App folder: dist\app\PikPakTextImporter
echo Installer: dist\installer\PikPakTextImporter-Setup.exe
pause
