@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "OUT=%ROOT%\profile_media_live_captures\link_source_role_webview_overlay"
set "PAYLOAD=%OUT%\selected_link_source_role_overlay.json"
set "CHANGES=%OUT%\selected_link_source_role_overlay_changes.jsonl"
set "DB=%OUT%\selected_link_source_role_roleplan.sqlite"
set "SUMMARY=%OUT%\selected_link_source_role_roleplan_summary.json"
if not exist "%PAYLOAD%" (
  echo Missing payload: %PAYLOAD%
  exit /b 1
)
py -3 "%~dp0r42be_source_role_db.py" sync --root "%ROOT%" --payload "%PAYLOAD%" --changes "%CHANGES%" --db "%DB%" --summary "%SUMMARY%"
if errorlevel 1 python "%~dp0r42be_source_role_db.py" sync --root "%ROOT%" --payload "%PAYLOAD%" --changes "%CHANGES%" --db "%DB%" --summary "%SUMMARY%"
endlocal
