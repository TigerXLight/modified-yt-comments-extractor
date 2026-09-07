@echo off
setlocal
cd /d "%~dp0..\.."
if "%~1"=="" (
  echo Usage: decide_r42dn_normal_access_route.cmd SOURCE [source_kind] [adapter_id]
  exit /b 2
)
call "%~dp0_r42dn_python.cmd" profile_media_normal_access_layer_r42dn.py "%~1" "%~2" --adapter-id "%~3"
exit /b %ERRORLEVEL%
