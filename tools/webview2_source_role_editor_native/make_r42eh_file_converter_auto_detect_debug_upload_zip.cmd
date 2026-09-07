@echo off
setlocal
cd /d "%~dp0..\.."
call tools\webview2_source_role_editor_native\_r42eh_python.cmd tools\webview2_source_role_editor_native\make_r42eh_file_converter_auto_detect_debug_upload_zip.py
