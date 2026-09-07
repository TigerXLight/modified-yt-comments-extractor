@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42EB] Building bounded local-fixture URL-guard debug upload ZIP...
call "%~dp0_r42eb_python.cmd" tools\webview2_source_role_editor_native\make_r42eb_archive_role_local_fixture_debug_upload_zip.py
exit /b %ERRORLEVEL%
