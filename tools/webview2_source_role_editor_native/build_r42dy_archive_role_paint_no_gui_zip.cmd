@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%" || exit /b 1
echo [R42DY] Building no-GUI archive role-paint reference ZIP...
call tools\webview2_source_role_editor_native\probe_r42dy_archive_role_paint_no_gui.cmd
call tools\webview2_source_role_editor_native\_r42dy_python.cmd tools\webview2_source_role_editor_native\build_r42dy_archive_role_paint_no_gui_zip.py
endlocal
