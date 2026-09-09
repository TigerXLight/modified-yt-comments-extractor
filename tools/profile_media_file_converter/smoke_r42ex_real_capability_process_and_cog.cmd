@echo off
setlocal
cd /d "%~dp0\..\.."
echo [R42EX] Running real capability/process/cog smoke. No network/WebView2/archive.ph.
py -3.11 -m py_compile main.py profile_media_file_converter_r42eh.py || exit /b 1
py -3.11 profile_media_file_converter_r42eh_test.py || exit /b 1
py -3.11 tools\profile_media_file_converter\probe_r42ex_real_capability_alignment_no_gui.py || exit /b 1
echo [DONE] R42EX smoke passed.
