@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%" || exit /b 1
echo [R42DV] Probing native role-paint JS/counter fix...
call tools\webview2_source_role_editor_native\_r42dv_python.cmd tools\webview2_source_role_editor_native\probe_r42dv_native_role_paint_js_fix.py || exit /b 1
endlocal
