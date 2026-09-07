@echo off
setlocal
cd /d "%~dp0\..\.."
echo [R42DT] Building archive native WebView2 bridge reference ZIP...
call tools\webview2_source_role_editor_native\_r42dt_python.cmd tools\webview2_source_role_editor_native\build_r42dt_archive_native_webview2_bridge_zip.py
