@echo off
setlocal
cd /d "%~dp0\..\.."
echo [R42EU] Running scrollable Advanced tabs/resolution settings smoke. No GUI/WebView2/archive.ph/network.
py -3.11 -m py_compile main.py profile_media_file_converter_r42eh.py || exit /b 1
py -3.11 profile_media_file_converter_r42eh_test.py || exit /b 1
py -3.11 tools\profile_media_file_converter\probe_r42eu_scrollable_advanced_tabs_resolution_settings_no_gui.py || exit /b 1
echo [DONE] R42EU smoke passed.
