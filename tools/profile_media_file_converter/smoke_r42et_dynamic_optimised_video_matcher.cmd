@echo off
setlocal
cd /d "%~dp0\..\.."
echo [R42ET] Running dynamic Optimised matcher smoke. No GUI/WebView2/archive.ph/network.
py -3.11 profile_media_file_converter_r42eh_test.py || exit /b 1
py -3.11 tools\profile_media_file_converter\probe_r42et_dynamic_optimised_video_matcher_no_gui.py || exit /b 1
echo [DONE] R42ET smoke passed.
