@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%" || exit /b 1
echo [R42DW] Probing native log for role-ready payload/paint markers...
call tools\webview2_source_role_editor_native\_r42dw_python.cmd tools\webview2_source_role_editor_native\probe_r42dw_native_role_overlay_log.py
endlocal
