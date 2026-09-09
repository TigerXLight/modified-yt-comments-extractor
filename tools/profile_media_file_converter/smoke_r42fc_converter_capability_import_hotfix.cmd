@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42FC] Running File Converter capability matrix import hotfix smoke. No network/WebView2/archive.ph.
py -3.11 tools\profile_media_file_converter\probe_r42fc_converter_capability_import_hotfix_no_gui.py
if errorlevel 1 exit /b 1
echo [DONE] R42FC smoke passed.
