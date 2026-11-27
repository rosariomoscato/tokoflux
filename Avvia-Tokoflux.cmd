@echo off
cd /d "%~dp0"
where uv >nul 2>nul
if errorlevel 1 (
  echo uv non trovato / uv was not found on PATH.
  pause
  exit /b 1
)
title Tokoflux
uv run --no-project --python 3.12 server.py
if errorlevel 1 pause
