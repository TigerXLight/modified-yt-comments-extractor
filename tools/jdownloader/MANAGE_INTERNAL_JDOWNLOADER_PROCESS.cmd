@echo off
setlocal
cd /d "%~dp0..\.."
set "PY=C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe"
if exist "venv\Scripts\python.exe" (
  "venv\Scripts\python.exe" -c "import sys; raise SystemExit(0)" >nul 2>nul
  if not errorlevel 1 set "PY=venv\Scripts\python.exe"
)
if not exist "%PY%" set "PY=python"
if "%~1"=="" (
  echo Usage: tools\jdownloader\MANAGE_INTERNAL_JDOWNLOADER_PROCESS.cmd start^|status^|probe^|stop
  exit /b 2
)
"%PY%" jdownloader_internal_process.py %*
exit /b %ERRORLEVEL%
