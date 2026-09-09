@echo off
cd /d "%~dp0..\.."
py -3.11 tools\profile_media_file_converter\audit_r42ev_converter_processes_efficiency_no_gui.py --benchmark
