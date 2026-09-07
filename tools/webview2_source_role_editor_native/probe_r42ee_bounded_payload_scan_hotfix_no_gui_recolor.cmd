@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42EE] NO-GUI / NO-NETWORK bounded payload-scan hotfix probe with recolour flag...
call tools\webview2_source_role_editor_native\_r42ee_python.cmd tools\webview2_source_role_editor_native\probe_r42ee_bounded_payload_scan_hotfix_no_gui.py --recolor
exit /b %ERRORLEVEL%
