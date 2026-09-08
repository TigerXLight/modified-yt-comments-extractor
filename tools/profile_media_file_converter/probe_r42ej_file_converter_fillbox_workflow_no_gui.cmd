@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42EJ] NO-GUI / NO-NETWORK fill-box converter workflow probe...
call tools\profile_media_file_converter\_r42ei_python.cmd tools\profile_media_file_converter\probe_r42ej_file_converter_fillbox_workflow_no_gui.py
