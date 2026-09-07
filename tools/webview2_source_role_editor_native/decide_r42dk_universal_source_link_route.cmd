@echo off
setlocal
cd /d "%~dp0..\.."
if "%~1"=="" (
  echo Usage: decide_r42dk_universal_source_link_route.cmd SOURCE [source_kind] [adapter_id]
  exit /b 2
)
call tools\webview2_source_role_editor_native\_r42dk_python.cmd profile_media_universal_source_link_adapter_r42dk.py "%~1" "%~2" --adapter-id "%~3" --output-root "profile_media_live_captures\r42dk_universal_source_link_adapter\cli_decisions"
exit /b %ERRORLEVEL%
