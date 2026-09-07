@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42DM] Probing normal access vs restricted Tor/Camoufox escalation...
set "OUT=profile_media_live_captures\r42dm_normal_access_first_escalation\probe_%DATE:~-4%%DATE:~3,2%%DATE:~0,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
set "OUT=%OUT: =0%"
mkdir "%OUT%" >nul 2>nul
call tools\webview2_source_role_editor_native\_r42dm_python.cmd profile_media_access_escalation_policy_r42dm.py "https://example.com/article" --status success --browser-status success --article-status ok --output-dir "%OUT%\normal_success" > "%OUT%\normal_success.json"
call tools\webview2_source_role_editor_native\_r42dm_python.cmd profile_media_access_escalation_policy_r42dm.py "https://example.com/article" --status browser_capture_failed --browser-status "HTTP 429 too many requests" --article-status empty --warning "HTTP 429 too many requests" --output-dir "%OUT%\restricted_429" > "%OUT%\restricted_429.json"
call tools\webview2_source_role_editor_native\_r42dm_python.cmd profile_media_access_escalation_policy_r42dm.py "https://archive.ph/6mr3C" --status browser_capture_failed --browser-status "recaptcha challenge" --article-status empty --output-dir "%OUT%\archive_owned" > "%OUT%\archive_owned.json"
call tools\webview2_source_role_editor_native\_r42dm_python.cmd profile_media_universal_source_link_adapter_r42dk.py "https://archive.ph/6mr3C" > "%OUT%\r42dk_archive_route.json"
call tools\webview2_source_role_editor_native\_r42dm_python.cmd profile_media_universal_source_link_adapter_r42dl.py "https://archive.ph/6mr3C" --summary > "%OUT%\r42dl_webview2_summary.txt"
echo [DONE] Probe output: %OUT%
type "%OUT%\normal_success.json"
type "%OUT%\restricted_429.json"
type "%OUT%\archive_owned.json"
