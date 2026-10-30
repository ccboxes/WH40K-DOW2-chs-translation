@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_font.ps1"
if errorlevel 1 (
    echo.
    echo Font patch installation failed. See the message above.
) else (
    echo.
    echo Font patch installation finished.
)
pause
