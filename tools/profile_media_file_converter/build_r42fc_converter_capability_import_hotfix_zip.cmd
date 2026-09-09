@echo off
setlocal
cd /d "%~dp0..\.."
py -3.11 tools\profile_media_file_converter\build_r42fc_converter_capability_import_hotfix_zip.py
