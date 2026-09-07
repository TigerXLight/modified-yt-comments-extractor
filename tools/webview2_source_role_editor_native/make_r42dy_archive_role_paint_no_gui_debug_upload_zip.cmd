@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%" || exit /b 1
echo [R42DY] Building bounded no-GUI archive role-paint debug upload ZIP...
call tools\webview2_source_role_editor_native\_r42dy_python.cmd tools\webview2_source_role_editor_native\make_r42dy_archive_role_paint_no_gui_debug_upload_zip.py
endlocal
