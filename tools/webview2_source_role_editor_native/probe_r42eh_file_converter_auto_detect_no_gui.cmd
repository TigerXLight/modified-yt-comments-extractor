@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42EH] NO-GUI / NO-NETWORK file converter auto-detect probe...
call tools\webview2_source_role_editor_native\_r42eh_python.cmd tools\webview2_source_role_editor_native\probe_r42eh_file_converter_auto_detect_no_gui.py
