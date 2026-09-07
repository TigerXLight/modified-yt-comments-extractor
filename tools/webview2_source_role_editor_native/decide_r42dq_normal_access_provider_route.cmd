@echo off
setlocal
cd /d "%~dp0..\.."
if "%~1"=="" (
  echo Usage: %~nx0 ^<source-or-uri^> [source_kind] [adapter_id] [--restricted-429] [--archive-owned]
  exit /b 2
)
call "%~dp0_r42dq_python.cmd" profile_media_normal_access_provider_layer_r42dq.py %*
exit /b %ERRORLEVEL%
