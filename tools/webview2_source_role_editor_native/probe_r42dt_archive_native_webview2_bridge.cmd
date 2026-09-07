@echo off
setlocal
cd /d "%~dp0\..\.."
echo [R42DT] Probing archive native WebView2 material bridge resolution...
call tools\webview2_source_role_editor_native\_r42dt_python.cmd tools\webview2_source_role_editor_native\probe_r42dt_archive_native_webview2_bridge.py
if errorlevel 1 exit /b %errorlevel%
echo [DONE] R42DT probe completed without starting WebView2/network.
