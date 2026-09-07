@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42EA] Queueing role_overlay_refresh ONLY if native warm server is already alive.
echo [R42EA] This command does not start the app/helper and does not navigate archive.ph.
call tools\webview2_source_role_editor_native\_r42ea_python.cmd tools\webview2_source_role_editor_native\queue_r42ea_role_refresh_if_native_server_already_loaded.py
