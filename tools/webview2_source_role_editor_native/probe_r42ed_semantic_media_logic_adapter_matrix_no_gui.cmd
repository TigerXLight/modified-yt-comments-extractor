@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42ED] NO-GUI / NO-NETWORK semantic-media logic and adapter guard matrix audit...
call tools\webview2_source_role_editor_native\_r42ed_python.cmd tools\webview2_source_role_editor_native\probe_r42ed_semantic_media_logic_adapter_matrix_no_gui.py
exit /b %ERRORLEVEL%
