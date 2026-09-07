@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42ED] Building semantic/media logic + adapter matrix reference ZIP...
call tools\webview2_source_role_editor_native\_r42ed_python.cmd tools\webview2_source_role_editor_native\build_r42ed_semantic_media_logic_adapter_matrix_zip.py
exit /b %ERRORLEVEL%
