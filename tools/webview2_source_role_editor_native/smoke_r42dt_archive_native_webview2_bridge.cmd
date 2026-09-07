@echo off
setlocal
cd /d "%~dp0\..\.."
echo [R42DT] Running archive native WebView2 bridge smoke tests...
call tools\webview2_source_role_editor_native\_r42dt_python.cmd -m py_compile profile_media_archive_material_chain_r42ct.py profile_media_link_source_real_webview_overlay_v83d.py profile_media_archive_native_webview2_bridge_r42dt_test.py
if errorlevel 1 exit /b %errorlevel%
call tools\webview2_source_role_editor_native\_r42dt_python.cmd tools\webview2_source_role_editor_native\probe_r42dt_archive_native_webview2_bridge.py
if errorlevel 1 exit /b %errorlevel%
echo [DONE] R42DT smoke passed without pytest and without launching network/browser.
