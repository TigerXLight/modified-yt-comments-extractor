@echo off
setlocal
echo [R42DZ] Building bounded no-GUI archive role-refresh dispatch debug upload ZIP...
call "%~dp0_r42dz_python.cmd" tools\webview2_source_role_editor_native\make_r42dz_archive_role_refresh_dispatch_no_gui_debug_upload_zip.py
endlocal
