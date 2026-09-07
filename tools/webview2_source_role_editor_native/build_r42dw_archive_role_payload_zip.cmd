@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%" || exit /b 1
echo [R42DW] Building archive role-payload-after-material reference ZIP...
call tools\webview2_source_role_editor_native\probe_r42dw_archive_role_payload_from_latest.cmd
call tools\webview2_source_role_editor_native\_r42dw_python.cmd tools\webview2_source_role_editor_native\build_r42dw_archive_role_payload_zip.py
endlocal
