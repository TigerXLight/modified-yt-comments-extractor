@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42ED] Building bounded semantic/media logic matrix debug upload ZIP...
call tools\webview2_source_role_editor_native\_r42ed_python.cmd tools\webview2_source_role_editor_native\make_r42ed_semantic_media_logic_adapter_matrix_debug_upload_zip.py
exit /b %ERRORLEVEL%
