@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42EF] Building compact bounded debug upload ZIP. No GUI/WebView2/archive.ph.
call tools\webview2_source_role_editor_native\_r42ef_python.cmd tools\webview2_source_role_editor_native\make_r42ef_bounded_debug_upload_zip.py
exit /b %ERRORLEVEL%
