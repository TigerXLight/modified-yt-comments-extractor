@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42DK] Probing universal source/link route decisions...
call tools\webview2_source_role_editor_native\decide_r42dk_universal_source_link_route.cmd "https://archive.ph/6mr3C"
call tools\webview2_source_role_editor_native\decide_r42dk_universal_source_link_route.cmd "T:\evidence\clip.mp4"
call tools\webview2_source_role_editor_native\decide_r42dk_universal_source_link_route.cmd "slack://workspace/channel/message/123" channel account_channel
echo [DONE] R42DK probe decisions written under profile_media_live_captures\r42dk_universal_source_link_adapter\cli_decisions
