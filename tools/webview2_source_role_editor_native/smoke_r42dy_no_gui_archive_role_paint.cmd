@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%" || exit /b 1
echo [R42DY] Running no-GUI archive role-paint smoke tests...
call tools\webview2_source_role_editor_native\_r42dy_python.cmd -m py_compile profile_media_archive_role_payload_cmd_replay_r42dy.py || exit /b 1
call tools\webview2_source_role_editor_native\_r42dy_python.cmd profile_media_archive_role_payload_cmd_replay_r42dy.py --self-test || exit /b 1
echo [R42DY] Checking existing R42DW command-line import path...
call tools\webview2_source_role_editor_native\_r42dy_python.cmd -m py_compile tools\webview2_source_role_editor_native\probe_r42dw_archive_role_payload_from_latest.py || exit /b 1
call tools\webview2_source_role_editor_native\_r42dy_python.cmd -m py_compile tools\webview2_source_role_editor_native\launch_r42dw_native_overlay_from_latest.py || exit /b 1
echo [DONE] R42DY no-GUI smoke passed.
endlocal
