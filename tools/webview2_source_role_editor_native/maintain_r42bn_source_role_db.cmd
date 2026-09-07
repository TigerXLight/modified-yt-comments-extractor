@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "OUT=%ROOT%\profile_media_live_captures\link_source_role_webview_overlay"
set "DB=%OUT%\selected_link_source_role_roleplan.sqlite"
if not exist "%DB%" (
  echo Missing R42BN source-role DB: %DB%
  echo Open a source-role editor once, or run sync_r42bn_source_role_db.cmd.
  exit /b 1
)
py -3 "%~dp0r42bn_source_role_db.py" maintain --db "%DB%" --keep-sessions-per-url 25 --keep-events 5000 --vacuum
if errorlevel 1 python "%~dp0r42bn_source_role_db.py" maintain --db "%DB%" --keep-sessions-per-url 25 --keep-events 5000 --vacuum
endlocal
