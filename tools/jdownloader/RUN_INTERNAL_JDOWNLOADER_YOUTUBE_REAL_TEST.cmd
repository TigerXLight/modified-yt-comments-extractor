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
  echo Usage: tools\jdownloader\RUN_INTERNAL_JDOWNLOADER_YOUTUBE_REAL_TEST.cmd "https://youtu.be/uyy2MhKyL9A?si=6dpOf1E9EdXxFtJk"
  exit /b 2
)
echo Running YTCE internal JDownloader real YouTube test.
echo No yt-dlp fallback will be used by this command.
echo URL normalization and CNL route attempts are recorded in the manifest.
"%PY%" jdownloader_internal_job.py "%~1" --package-name "YTCE internal JD real test" --video --audio --image --description --wait --cnl-route-timeout-seconds 8 --cnl-total-timeout-seconds 30 --monitor-timeout-seconds 90 --overall-timeout-seconds 150 --timeout-seconds 90
exit /b %ERRORLEVEL%
