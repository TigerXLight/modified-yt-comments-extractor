@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%" || exit /b 1
echo [R42DV] Building bounded active native role-paint debug upload ZIP...
call tools\webview2_source_role_editor_native\_r42dv_python.cmd tools\webview2_source_role_editor_native\make_r42dv_active_native_role_paint_debug_upload_zip.py || exit /b 1
endlocal
