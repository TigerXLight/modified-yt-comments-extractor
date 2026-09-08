@echo off
setlocal
cd /d "%~dp0..\.."
call tools\profile_media_file_converter\_r42ei_python.cmd tools\profile_media_file_converter\make_r42en_file_converter_review_fillbox_clone_text_fix_debug_upload_zip.py
