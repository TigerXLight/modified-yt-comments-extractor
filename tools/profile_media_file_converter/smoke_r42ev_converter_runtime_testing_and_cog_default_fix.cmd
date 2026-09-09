@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42EV] Running converter runtime/cog/default fix smoke. No GUI/WebView2/archive.ph/network.
py -3.11 profile_media_file_converter_r42eh_test.py || exit /b 1
py -3.11 tools\profile_media_file_converter\probe_r42ev_converter_runtime_testing_and_cog_default_fix_no_gui.py || exit /b 1
py -3.11 tools\profile_media_file_converter\audit_r42ev_converter_processes_efficiency_no_gui.py --no-benchmark || exit /b 1
echo [DONE] R42EV smoke passed.
