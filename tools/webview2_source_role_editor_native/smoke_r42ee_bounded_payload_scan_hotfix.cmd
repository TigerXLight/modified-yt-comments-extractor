@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42EE] Running bounded payload-scan hotfix smoke tests...
call tools\webview2_source_role_editor_native\_r42ee_python.cmd profile_media_semantic_media_logic_matrix_r42ee_test.py
if errorlevel 1 exit /b %ERRORLEVEL%
echo [R42EE] Static-checking no unbounded Path.rglob over live captures...
call tools\webview2_source_role_editor_native\_r42ee_python.cmd -c "from pathlib import Path; import json; t=Path('profile_media_semantic_media_logic_matrix_r42ed.py').read_text(encoding='utf-8', errors='replace'); checks={'bounded_safe_walk_present':'_safe_walk_payload_files' in t,'reparse_guard_present':'FILE_ATTRIBUTE_REPARSE_POINT' in t,'payload_scan_roots_present':'_PAYLOAD_SCAN_ROOT_NAMES' in t,'old_payload_rglob_absent':'base.rglob(\"archive_role_overlay_payload_r42dw.json\")' not in t and '.rglob(\"archive_role_overlay_payload_r42dw.json\")' not in t}; print(json.dumps(checks, indent=2)); raise SystemExit(0 if all(checks.values()) else 2)"
if errorlevel 1 exit /b %ERRORLEVEL%
echo [DONE] R42EE smoke passed without opening GUI/WebView2/archive.ph.
