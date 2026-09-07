@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%" || exit /b 1
echo [R42DX] Building command-line archive role-payload reference ZIP...
call tools\webview2_source_role_editor_native\probe_r42dx_archive_role_payload_no_gui.cmd
if errorlevel 1 exit /b %errorlevel%
call tools\webview2_source_role_editor_native\_r42dx_python.cmd tools\webview2_source_role_editor_native\build_r42dx_cmdline_archive_role_payload_zip.py
endlocal
