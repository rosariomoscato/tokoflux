@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Installa-Tokoflux.ps1"
echo.
pause
