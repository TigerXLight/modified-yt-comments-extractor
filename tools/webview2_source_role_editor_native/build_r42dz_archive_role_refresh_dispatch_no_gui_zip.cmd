@echo off
setlocal
echo [R42DZ] Building no-GUI archive role-refresh dispatch reference ZIP...
call "%~dp0_r42dz_python.cmd" tools\webview2_source_role_editor_native\build_r42dz_archive_role_refresh_dispatch_no_gui_zip.py
endlocal
