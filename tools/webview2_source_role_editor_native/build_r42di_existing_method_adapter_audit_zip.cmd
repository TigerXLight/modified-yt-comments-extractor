@echo off
setlocal
cd /d "%~dp0\..\.."
echo [R42DI] Building existing-method adapter audit ZIP...
call tools\webview2_source_role_editor_native\_r42di_python.cmd profile_media_existing_method_adapter_audit_r42di.py --audit --zip
exit /b %ERRORLEVEL%
