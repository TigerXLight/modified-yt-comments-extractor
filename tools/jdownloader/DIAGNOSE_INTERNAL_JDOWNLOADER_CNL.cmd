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
  echo Usage: tools\jdownloader\DIAGNOSE_INTERNAL_JDOWNLOADER_CNL.cmd "https://youtu.be/uyy2MhKyL9A?si=6dpOf1E9EdXxFtJk"
  echo Add --submit only when you intentionally want to send a guarded CNL submission to the project-local runtime.
  exit /b 2
)
echo Diagnosing YTCE internal JDownloader CNL routes.
echo Dry-run route/readiness inspection by default; no job is submitted unless --submit is supplied.
"%PY%" jdownloader_internal_cnl.py %*
exit /b %ERRORLEVEL%
