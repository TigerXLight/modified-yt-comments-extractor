@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42FA] Running File Converter cog seam repair smoke. No network/WebView2/archive.ph.
py -3.11 tools\profile_media_file_converter\probe_r42fa_file_converter_cog_seam_repair_no_gui.py
if errorlevel 1 exit /b 1
echo [DONE] R42FA smoke passed.
