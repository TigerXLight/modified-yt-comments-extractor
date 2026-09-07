@echo off
setlocal
cd /d "%~dp0..\.."
if "%~1"=="" (
  echo Usage: %~nx0 SOURCE [ADAPTER_ID] [PHASE]
  exit /b 2
)
set "SRC=%~1"
set "ADAPTER=%~2"
if "%ADAPTER%"=="" set "ADAPTER=webpage"
set "PHASE=%~3"
if "%PHASE%"=="" set "PHASE=cli"
call "%~dp0_r42do_python.cmd" profile_media_universal_worker_source_router_r42do.py "%SRC%" "%ADAPTER%" "%PHASE%"
