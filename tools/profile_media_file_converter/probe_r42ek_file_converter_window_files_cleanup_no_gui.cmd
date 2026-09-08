@echo off
setlocal
cd /d "%~dp0..\.."
py -3.11 tools\profile_media_file_converter\probe_r42ek_file_converter_window_files_cleanup_no_gui.py
exit /b %ERRORLEVEL%
