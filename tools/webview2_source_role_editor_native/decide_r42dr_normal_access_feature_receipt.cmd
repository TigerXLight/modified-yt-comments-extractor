@echo off
setlocal
cd /d "%~dp0..\.."
call tools\webview2_source_role_editor_native\_r42dr_python.cmd profile_media_normal_access_feature_receipts_r42dr.py %*
exit /b %ERRORLEVEL%
