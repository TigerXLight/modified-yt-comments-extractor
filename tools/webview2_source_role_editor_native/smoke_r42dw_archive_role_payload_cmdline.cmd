@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%" || exit /b 1
echo [R42DW] Running archive role-payload command-line smoke tests...
call tools\webview2_source_role_editor_native\_r42dw_python.cmd -m py_compile profile_media_archive_role_payload_r42dw.py profile_media_archive_role_payload_r42dw_test.py profile_media_link_source_real_webview_overlay_v83d.py
if errorlevel 1 exit /b 1
call tools\webview2_source_role_editor_native\_r42dw_python.cmd profile_media_archive_role_payload_r42dw_test.py
if errorlevel 1 exit /b 1
echo [R42DW] Checking Program.cs markers...
call tools\webview2_source_role_editor_native\_r42dw_python.cmd -c "from pathlib import Path; p=Path('tools/webview2_source_role_editor_native/Program.cs'); t=p.read_text(encoding='utf-8',errors='replace'); checks={'role_overlay_refresh_branch':'role_overlay_refresh' in t,'refresh_applied_log':'r42dw_role_overlay_refresh_applied' in t,'counts_logged':'counts_semantic=' in t and 'counts_media=' in t,'payload_mode_counter':'CountPayloadModeRows' in t}; import json,sys; print(json.dumps(checks,indent=2)); sys.exit(0 if all(checks.values()) else 2)"
if errorlevel 1 exit /b 1
echo [R42DW] Resetting stale native helper before rebuild...
call tools\webview2_source_role_editor_native\reset_r42dw_native_webview2_server.cmd
echo [R42DW] Building native WebView2 helper with role-overlay refresh branch...
dotnet build tools\webview2_source_role_editor_native\YTCE.NativeSourceRoleEditor.csproj -c Release
if errorlevel 1 exit /b 1
echo [DONE] R42DW smoke/build passed.
endlocal
