@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42EA] NO-GUI / NO-NETWORK app-side archive role-refresh live-spool audit with recolor payload...
call tools\webview2_source_role_editor_native\_r42ea_python.cmd tools\webview2_source_role_editor_native\probe_r42ea_archive_role_refresh_live_spool_no_gui.py --recolor
