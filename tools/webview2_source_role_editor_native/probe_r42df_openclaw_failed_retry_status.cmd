@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42DF] Failed-install retry manifest summary...
call tools\webview2_source_role_editor_native\_r42df_python.cmd profile_media_openclaw_failed_marketplace_retry_r42df.py summary
exit /b %ERRORLEVEL%
