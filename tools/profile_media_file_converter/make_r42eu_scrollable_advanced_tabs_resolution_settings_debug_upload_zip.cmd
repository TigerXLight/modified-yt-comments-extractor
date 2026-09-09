@echo off
setlocal
cd /d "%~dp0\..\.."
py -3.11 tools\profile_media_file_converter\make_r42eu_scrollable_advanced_tabs_resolution_settings_debug_upload_zip.py
