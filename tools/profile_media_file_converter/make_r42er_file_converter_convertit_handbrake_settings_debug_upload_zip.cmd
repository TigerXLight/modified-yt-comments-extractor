@echo off
setlocal
cd /d "%~dp0\..\.."
py -3.11 tools\profile_media_file_converter\make_r42er_file_converter_convertit_handbrake_settings_debug_upload_zip.py
