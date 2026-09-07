@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "OUT=%ROOT%\profile_media_live_captures\link_source_role_webview_overlay"
set "DB=%OUT%\selected_link_source_role_roleplan.sqlite"
if not exist "%DB%" (
  echo Missing R42BQ source-role DB: %DB%
  echo Open a source-role editor once, or run sync_r42bq_source_role_db.cmd.
  exit /b 1
)
py -3 "%~dp0r42bq_source_role_db.py" inspect --db "%DB%"
if errorlevel 1 python "%~dp0r42bq_source_role_db.py" inspect --db "%DB%"
endlocal
