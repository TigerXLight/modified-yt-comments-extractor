@echo off
setlocal
cd /d "%~dp0\..\.."
echo [R42ER] Running File Converter Convertit/HandBrake settings smoke. No GUI/WebView2/archive.ph/network.
py -3.11 -m py_compile main.py profile_media_file_converter_r42eh.py
if errorlevel 1 exit /b 1
py -3.11 profile_media_file_converter_r42eh_test.py
if errorlevel 1 exit /b 1
py -3.11 tools\profile_media_file_converter\probe_r42er_file_converter_convertit_handbrake_settings_no_gui.py
if errorlevel 1 exit /b 1
echo [DONE] R42ER smoke passed.
