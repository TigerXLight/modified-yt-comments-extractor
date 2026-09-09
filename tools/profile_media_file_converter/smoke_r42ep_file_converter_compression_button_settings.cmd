@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42EP] Running file converter compression button/settings polish smoke. No GUI/WebView2/archive.ph/network.
call tools\profile_media_file_converter\_r42ei_python.cmd -m py_compile main.py profile_media_file_converter_r42eh.py profile_media_file_converter_r42eg.py profile_media_file_converter_r42eh_test.py tools\profile_media_file_converter\probe_r42ep_file_converter_compression_button_settings_no_gui.py || exit /b 1
call tools\profile_media_file_converter\_r42ei_python.cmd profile_media_file_converter_r42eh_test.py || exit /b 1
call tools\profile_media_file_converter\_r42ei_python.cmd tools\profile_media_file_converter\probe_r42ep_file_converter_compression_button_settings_no_gui.py || exit /b 1
echo [DONE] R42EP smoke passed.
