@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42DO] Probing universal worker source-router contexts...
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set STAMP=%%i
set "OUT=profile_media_live_captures\r42do_universal_worker_source_router\probe_%STAMP%"
call "%~dp0_r42do_python.cmd" profile_media_universal_worker_source_router_r42do.py --probe --output-dir "%OUT%"
if errorlevel 1 exit /b %ERRORLEVEL%
echo [DONE] Probe output: %OUT%
