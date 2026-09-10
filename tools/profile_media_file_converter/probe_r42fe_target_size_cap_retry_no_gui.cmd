@echo off
setlocal
cd /d "%~dp0\..\.."
py -3.11 tools\profile_media_file_converter\probe_r42fe_target_size_cap_retry_no_gui.py %*
