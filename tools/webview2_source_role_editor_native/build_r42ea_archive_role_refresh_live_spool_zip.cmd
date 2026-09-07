@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42EA] Building no-GUI archive role-refresh live-spool reference ZIP...
call tools\webview2_source_role_editor_native\_r42ea_python.cmd tools\webview2_source_role_editor_native\build_r42ea_archive_role_refresh_live_spool_zip.py
