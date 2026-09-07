@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42EA] Running no-GUI/no-network archive role-refresh live-spool smoke tests...
call tools\webview2_source_role_editor_native\_r42ea_python.cmd -m py_compile profile_media_archive_role_refresh_live_spool_r42ea.py profile_media_archive_role_refresh_live_spool_r42ea_test.py main.py
if errorlevel 1 exit /b %ERRORLEVEL%
call tools\webview2_source_role_editor_native\_r42ea_python.cmd profile_media_archive_role_refresh_live_spool_r42ea.py --self-test
if errorlevel 1 exit /b %ERRORLEVEL%
echo [R42EA] Checking app-side R42EA markers...
call tools\webview2_source_role_editor_native\_r42ea_python.cmd -c "from pathlib import Path; m=Path('main.py').read_text(encoding='utf-8',errors='replace'); p=Path('profile_media_archive_role_refresh_live_spool_r42ea.py').read_text(encoding='utf-8',errors='replace'); assert 'spool_live_role_overlay_refresh_if_server_ready' in m; assert 'native_server_not_ready_no_gui_no_start' in p; assert 'role_overlay_refresh' in p; print('[DONE] R42EA app-side markers present.')"
if errorlevel 1 exit /b %ERRORLEVEL%
echo [DONE] R42EA smoke passed without opening GUI/WebView2/archive.ph.
