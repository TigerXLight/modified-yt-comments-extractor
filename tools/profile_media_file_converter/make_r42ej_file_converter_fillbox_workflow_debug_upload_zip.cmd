@echo off
setlocal
cd /d "%~dp0..\.."
call tools\profile_media_file_converter\_r42ei_python.cmd tools\profile_media_file_converter\make_r42ej_file_converter_fillbox_workflow_debug_upload_zip.py
