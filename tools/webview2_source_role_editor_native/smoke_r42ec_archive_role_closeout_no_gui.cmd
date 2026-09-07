@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42EC] Running no-GUI/no-network archive role closeout smoke tests...
call "%~dp0_r42ec_python.cmd" profile_media_archive_role_local_fixture_r42eb_test.py || exit /b %ERRORLEVEL%
call "%~dp0_r42ec_python.cmd" profile_media_archive_role_closeout_r42ec.py --self-test || exit /b %ERRORLEVEL%
echo [R42EC] Checking Program.cs closeout markers...
call "%~dp0_r42ec_python.cmd" -c "from pathlib import Path; t=Path('tools/webview2_source_role_editor_native/Program.cs').read_text(encoding='utf-8', errors='replace'); import json; checks={'native_toolbar_state_success_log':'r42ec_state_applied=true' in t and '_log.Log(\"native_toolbar_state\"' in t, 'role_paint_ready':'r42dv_role_paint_js_ready' in t, 'p_s_t_u_count_log':'counts_semantic={semanticCountsText}; counts_media={mediaCountsText}' in t}; print(json.dumps(checks, indent=2)); raise SystemExit(0 if all(checks.values()) else 1)" || exit /b %ERRORLEVEL%
echo [R42EC] Building native WebView2 helper with explicit native_toolbar_state logging...
dotnet build tools\webview2_source_role_editor_native\YTCE.NativeSourceRoleEditor.csproj -c Release || exit /b %ERRORLEVEL%
echo [DONE] R42EC smoke/build passed without opening GUI/WebView2/archive.ph.
exit /b 0
