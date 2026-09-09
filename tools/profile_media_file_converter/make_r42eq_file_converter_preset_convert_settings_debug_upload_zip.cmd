@echo off
setlocal
cd /d "%~dp0..\.."
call tools\profile_media_file_converter\_r42ei_python.cmd tools\profile_media_file_converter\make_r42eq_file_converter_preset_convert_settings_debug_upload_zip.py
