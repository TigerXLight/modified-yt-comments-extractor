@echo off
setlocal
cd /d "%~dp0..\.."
py -3.11 tools\profile_media_file_converter\make_r42el_file_converter_review_style_held_rows_debug_upload_zip.py
exit /b %ERRORLEVEL%
