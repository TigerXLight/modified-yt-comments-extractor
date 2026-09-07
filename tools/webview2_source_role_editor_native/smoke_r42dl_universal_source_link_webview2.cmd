@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42DL] Running universal source/link WebView2 context smoke tests...
call tools\webview2_source_role_editor_native\_r42dl_python.cmd -m py_compile profile_media_universal_source_link_adapter_r42dl.py profile_media_link_source_details_role_matrix_v83d.py profile_media_link_source_webpage_role_view_v83d.py profile_media_link_source_real_webview_overlay_v83d.py
if errorlevel 1 exit /b %ERRORLEVEL%
call tools\webview2_source_role_editor_native\_r42dl_python.cmd profile_media_universal_source_link_adapter_r42dl_test.py
if errorlevel 1 exit /b %ERRORLEVEL%
call tools\webview2_source_role_editor_native\_r42dl_python.cmd source_adapters_test.py
if errorlevel 1 exit /b %ERRORLEVEL%
call tools\webview2_source_role_editor_native\_r42dl_python.cmd source_resource_state_test.py
if errorlevel 1 exit /b %ERRORLEVEL%
echo [DONE] R42DL smoke passed without pytest.
