@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42EC] Building bounded archive role closeout debug upload ZIP...
call "%~dp0_r42ec_python.cmd" tools\webview2_source_role_editor_native\make_r42ec_archive_role_closeout_debug_upload_zip.py
exit /b %ERRORLEVEL%
