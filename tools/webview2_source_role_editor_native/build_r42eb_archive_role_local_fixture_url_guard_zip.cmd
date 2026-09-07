@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42EB] Building archive role local-fixture URL-guard reference ZIP...
call "%~dp0_r42eb_python.cmd" profile_media_archive_role_local_fixture_r42eb.py "https://archive.ph/6mr3C"
call "%~dp0_r42eb_python.cmd" tools\webview2_source_role_editor_native\build_r42eb_archive_role_local_fixture_url_guard_zip.py
exit /b %ERRORLEVEL%
