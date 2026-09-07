@echo off
setlocal
cd /d "%~dp0\..\.."
echo [R42DS] Building archive source-role WebView2 reference ZIP...
call tools\webview2_source_role_editor_native\probe_r42ds_archive_source_roles_webview2.cmd
if errorlevel 1 exit /b 1
call tools\webview2_source_role_editor_native\_r42ds_python.cmd tools\webview2_source_role_editor_native\build_r42ds_archive_source_roles_webview2_zip.py
if errorlevel 1 exit /b 1
endlocal
