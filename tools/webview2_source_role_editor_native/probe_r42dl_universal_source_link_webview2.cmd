@echo off
setlocal
cd /d "%~dp0..\.."
set "OUT=profile_media_live_captures\r42dl_universal_source_link_webview2\probe_%DATE:~-4%%DATE:~3,2%%DATE:~0,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
set "OUT=%OUT: =0%"
mkdir "%OUT%" >nul 2>nul
echo [R42DL] Probing WebView2-visible universal source/link routes...
call tools\webview2_source_role_editor_native\_r42dl_python.cmd profile_media_universal_source_link_adapter_r42dl.py "https://archive.ph/6mr3C" --summary > "%OUT%\archive_route_summary.txt"
call tools\webview2_source_role_editor_native\_r42dl_python.cmd profile_media_universal_source_link_adapter_r42dl.py "slack://workspace/channel/message/123" channel --adapter-id account_channel --summary > "%OUT%\channel_route_summary.txt"
call tools\webview2_source_role_editor_native\_r42dl_python.cmd profile_media_universal_source_link_adapter_r42dl.py "T:\evidence\clip.mp4" --summary > "%OUT%\local_media_route_summary.txt"
call tools\webview2_source_role_editor_native\_r42dl_python.cmd profile_media_universal_source_link_adapter_r42dl.py "[https://archive.ph/6mr3C](https://archive.ph/6mr3C)" --summary > "%OUT%\markdown_url_normalization_summary.txt"
echo [DONE] Probe output: %CD%\%OUT%
type "%OUT%\archive_route_summary.txt"
