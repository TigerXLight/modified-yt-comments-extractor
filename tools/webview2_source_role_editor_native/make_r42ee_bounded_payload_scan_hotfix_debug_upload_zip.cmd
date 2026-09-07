@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42EE/R42EF] Building compact bounded payload-scan debug upload ZIP. No verbose audit_rows dump.
call tools\webview2_source_role_editor_native\_r42ef_python.cmd tools\webview2_source_role_editor_native\make_r42ee_bounded_payload_scan_hotfix_debug_upload_zip.py
exit /b %ERRORLEVEL%
