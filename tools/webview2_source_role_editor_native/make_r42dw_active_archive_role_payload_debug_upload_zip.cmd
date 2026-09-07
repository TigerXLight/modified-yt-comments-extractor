@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%" || exit /b 1
echo [R42DW] Building bounded active archive role-payload debug upload ZIP...
call tools\webview2_source_role_editor_native\_r42dw_python.cmd tools\webview2_source_role_editor_native\make_r42dw_active_archive_role_payload_debug_upload_zip.py
endlocal
