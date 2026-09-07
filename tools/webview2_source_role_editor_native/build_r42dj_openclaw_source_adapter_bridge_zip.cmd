@echo off
setlocal
pushd "%~dp0..\.." || exit /b 1
echo [R42DJ] Building OpenClaw source-adapter bridge ZIP...
call tools\webview2_source_role_editor_native\_r42dj_python.cmd profile_media_openclaw_source_adapter_bridge_r42dj.py --mode package --print-summary
set "RC=%ERRORLEVEL%"
popd
exit /b %RC%
