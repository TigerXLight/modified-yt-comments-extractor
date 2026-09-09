@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42EW] Running converter full-process/cog smoke. No network/WebView2/archive.ph.
py -3.11 -m py_compile main.py profile_media_file_converter_r42eh.py || exit /b 1
call tools\profile_media_file_converter\probe_r42ew_cog_and_capability_no_gui.cmd || exit /b 1
call tools\profile_media_file_converter\audit_r42ew_converter_full_pipeline_no_gui.cmd --timeout 45 --write-json || exit /b 1
echo [DONE] R42EW smoke passed.
