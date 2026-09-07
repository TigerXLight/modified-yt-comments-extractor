@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%" || exit /b 1
echo [R42DY] NO-GUI / NO-NETWORK archive role-paint replay with recolor style flag...
set "YTCE_R42DU_TEXT_PAINT_STYLE=recolor"
call tools\webview2_source_role_editor_native\_r42dy_python.cmd profile_media_archive_role_payload_cmd_replay_r42dy.py "https://archive.ph/6mr3C" --recolor
endlocal
