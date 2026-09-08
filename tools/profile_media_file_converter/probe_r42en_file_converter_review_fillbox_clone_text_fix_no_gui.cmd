@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42EN] NO-GUI / NO-NETWORK Review-fillbox clone probe...
call tools\profile_media_file_converter\_r42ei_python.cmd tools\profile_media_file_converter\probe_r42en_file_converter_review_fillbox_clone_text_fix_no_gui.py
