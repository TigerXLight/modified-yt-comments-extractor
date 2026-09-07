@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42EH] Running file converter auto-detect smoke tests. No GUI/WebView2/archive.ph/network.
call tools\webview2_source_role_editor_native\_r42eh_python.cmd -m py_compile main.py profile_media_file_converter_r42eh.py profile_media_file_converter_r42eh_test.py || exit /b 1
call tools\webview2_source_role_editor_native\_r42eh_python.cmd profile_media_file_converter_r42eh_test.py || exit /b 1
echo [R42EH] Checking main.py UI/backend markers...
call tools\webview2_source_role_editor_native\_r42eh_python.cmd -c "from pathlib import Path; import json; s=Path('main.py').read_text(encoding='utf-8', errors='replace'); q=chr(34); checks={'file_converter_button':('text='+q+'File Converter'+q) in s,'file_converter_section':'def _create_file_converter_section' in s,'converter_auto_target':('ctk.StringVar(value='+q+'auto'+q+')') in s,'converter_detect_display':'def _file_converter_detect_display' in s,'keep_icon_state':'session_file_keep_original' in s,'k_button_row':'_toggle_session_file_keep_original' in s,'backend_import':'profile_media_file_converter_r42eh' in s,'pytest_not_required':('-m ' + 'pytest') not in Path('tools/webview2_source_role_editor_native/smoke_r42eh_file_converter_auto_detect.cmd').read_text(encoding='utf-8', errors='replace')}; print(json.dumps(checks, indent=2)); raise SystemExit(0 if all(checks.values()) else 1)" || exit /b 1
echo [DONE] R42EH smoke passed.
