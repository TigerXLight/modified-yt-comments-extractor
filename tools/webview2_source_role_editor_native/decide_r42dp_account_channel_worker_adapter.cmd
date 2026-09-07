@echo off
setlocal
cd /d "%~dp0..\.."
if "%~1"=="" (
  echo Usage: %~nx0 ^<account-channel-uri^> [phase]
  exit /b 2
)
set "PHASE=%~2"
if "%PHASE%"=="" set "PHASE=cli"
call "%~dp0_r42dp_python.cmd" profile_media_account_channel_worker_adapter_r42dp.py "%~1" "%PHASE%"
exit /b %ERRORLEVEL%
