@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42EE] Building bounded payload-scan hotfix reference ZIP...
call tools\webview2_source_role_editor_native\_r42ee_python.cmd tools\webview2_source_role_editor_native\build_r42ee_bounded_payload_scan_hotfix_zip.py
exit /b %ERRORLEVEL%
