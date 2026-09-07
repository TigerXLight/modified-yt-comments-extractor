@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "YTCE_R42DU_TEXT_PAINT_STYLE=recolor"
cd /d "%ROOT%" || exit /b 1
echo [R42DW] Launching/refreshing native WebView2 from latest role-ready archive payload with recolour mode, without opening the full app...
call tools\webview2_source_role_editor_native\_r42dw_python.cmd tools\webview2_source_role_editor_native\launch_r42dw_native_overlay_from_latest.py
endlocal
