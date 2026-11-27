@echo off
cd /d "%TEMP%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Disinstalla-Tokoflux.ps1"
