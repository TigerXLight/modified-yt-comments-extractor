@echo off
setlocal
cd /d "%~dp0\..\.."
echo [R42DI] Existing media/document/source-method + OpenClaw adapter audit...
call tools\webview2_source_role_editor_native\_r42di_python.cmd profile_media_existing_method_adapter_audit_r42di.py --audit
exit /b %ERRORLEVEL%
