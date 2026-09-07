@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%" || exit /b 1
echo [R42DU] Building bounded active archive material/source-role debug upload ZIP...
call tools\webview2_source_role_editor_native\_r42du_python.cmd tools\webview2_source_role_editor_native\make_r42du_active_archive_material_debug_upload_zip.py || exit /b 1
endlocal
