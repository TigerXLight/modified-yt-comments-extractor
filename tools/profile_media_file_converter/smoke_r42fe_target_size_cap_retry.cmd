@echo off
setlocal
cd /d "%~dp0\..\.."
echo [R42FE] Running target-size cap retry smoke. No network/WebView2/archive.ph.
py -3.11 tools\profile_media_file_converter\probe_r42fe_target_size_cap_retry_no_gui.py
if errorlevel 1 exit /b 1
echo [DONE] R42FE smoke passed.
