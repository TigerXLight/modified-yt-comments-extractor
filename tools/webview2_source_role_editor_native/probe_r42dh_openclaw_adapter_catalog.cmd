@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42DH] Building OpenClaw adapter catalog...
call "tools\webview2_source_role_editor_native\_r42dh_python.cmd" profile_media_openclaw_adapter_catalog_r42dh.py --mode catalog
exit /b %ERRORLEVEL%
