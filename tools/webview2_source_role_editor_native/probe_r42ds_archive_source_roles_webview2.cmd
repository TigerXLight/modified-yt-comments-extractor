@echo off
setlocal
cd /d "%~dp0\..\.."
echo [R42DS] Probing archive source-role WebView2 surface...
call tools\webview2_source_role_editor_native\_r42ds_python.cmd tools\webview2_source_role_editor_native\probe_r42ds_archive_source_roles_webview2.py
if errorlevel 1 exit /b 1
endlocal
