@echo off
setlocal
cd /d "%~dp0\..\.."
echo [R42DS] Building active archive/source-role/WebView2 source upload ZIP...
call tools\webview2_source_role_editor_native\_r42ds_python.cmd tools\webview2_source_role_editor_native\make_r42ds_active_archive_source_roles_upload_zip.py
if errorlevel 1 exit /b 1
endlocal
