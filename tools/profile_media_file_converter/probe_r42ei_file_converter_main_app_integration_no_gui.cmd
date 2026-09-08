@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42EI] NO-GUI / NO-NETWORK main-app converter integration probe...
call tools\profile_media_file_converter\_r42ei_python.cmd tools\profile_media_file_converter\probe_r42ei_file_converter_main_app_integration_no_gui.py
