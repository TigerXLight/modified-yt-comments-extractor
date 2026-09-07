@echo off
setlocal
cd /d "%~dp0\..\.."
echo [R42DT] Building active archive native WebView2 bridge source/runtime upload ZIP...
call tools\webview2_source_role_editor_native\_r42dt_python.cmd tools\webview2_source_role_editor_native\make_r42dt_active_archive_native_bridge_upload_zip.py
