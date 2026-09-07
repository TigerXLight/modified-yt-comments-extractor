@echo off
setlocal
cd /d "%~dp0..\.."
if /I not "%~1"=="YES" (
  echo [FAIL] This explicitly enables OpenClaw memory-core.
  echo        Re-run exactly:
  echo        tools\webview2_source_role_editor_native\enable_r42dh_memory_core_explicit.cmd YES
  exit /b 2
)
echo [R42DH] Enabling OpenClaw memory-core with capability acceptance...
call "tools\webview2_source_role_editor_native\_r42dh_python.cmd" profile_media_openclaw_adapter_catalog_r42dh.py --mode enable-memory-core --yes
exit /b %ERRORLEVEL%
