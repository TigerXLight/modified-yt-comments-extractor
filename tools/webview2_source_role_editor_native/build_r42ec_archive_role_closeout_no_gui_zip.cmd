@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42EC] Building archive role closeout no-GUI reference ZIP...
call "%~dp0_r42ec_python.cmd" tools\webview2_source_role_editor_native\build_r42ec_archive_role_closeout_no_gui_zip.py
exit /b %ERRORLEVEL%
