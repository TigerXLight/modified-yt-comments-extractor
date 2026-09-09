@echo off
setlocal
cd /d "%~dp0..\.."
py -3.11 tools\profile_media_file_converter\audit_r42fc_converter_end_to_end_capability_matrix_no_gui.py %*
