@echo off
setlocal
cd /d "%~dp0\..\.."
py -3.11 tools\profile_media_file_converter\probe_r42et_dynamic_optimised_video_matcher_no_gui.py
