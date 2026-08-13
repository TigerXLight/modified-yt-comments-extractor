@echo off
setlocal
cd /d "%~dp0..\.."
set "PY=C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe"
if exist "venv\Scripts\python.exe" (
  "venv\Scripts\python.exe" -c "import sys; raise SystemExit(0)" >nul 2>nul
  if not errorlevel 1 set "PY=venv\Scripts\python.exe"
)
if not exist "%PY%" set "PY=python"
"%PY%" third_party\jdownloader\tools\build_internal_jdownloader_runtime.py %*
exit /b %ERRORLEVEL%
