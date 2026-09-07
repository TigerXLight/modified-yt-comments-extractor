@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42EF] Running bounded debug ZIP64 hotfix smoke tests...
call tools\webview2_source_role_editor_native\_r42ef_python.cmd profile_media_bounded_debug_zip_r42ef_test.py
if errorlevel 1 exit /b %ERRORLEVEL%
echo [R42EF] Static-checking compact upload builder...
call tools\webview2_source_role_editor_native\_r42ef_python.cmd tools\webview2_source_role_editor_native\smoke_r42ef_bounded_debug_zip64_hotfix.py
if errorlevel 1 exit /b %ERRORLEVEL%
echo [DONE] R42EF smoke passed. No GUI/WebView2/archive.ph was opened.
