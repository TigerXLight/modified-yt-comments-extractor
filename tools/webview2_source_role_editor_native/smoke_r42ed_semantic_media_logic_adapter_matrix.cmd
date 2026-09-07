@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42ED] Running semantic/media logic matrix and colour cleanup smoke tests...
call tools\webview2_source_role_editor_native\_r42ed_python.cmd profile_media_semantic_media_logic_matrix_r42ed_test.py
if errorlevel 1 exit /b %ERRORLEVEL%
echo [R42ED] Static-checking native WebView2 colour cleanup markers...
call tools\webview2_source_role_editor_native\_r42ed_python.cmd -c "from pathlib import Path; import json; p=Path('tools/webview2_source_role_editor_native/Program.cs'); t=p.read_text(encoding='utf-8', errors='replace'); checks={'r42ed_const': 'R42ED_ROLE_COLOR_CLEANUP' in t, 'role_labels': 'ROLE_LABELS' in t, 'css_vars': '--ytce-primary:#059669' in t, 'colour_cleanup_class': 'ytce-r42ed-text-colour-cleanup' in t, 'role_label_attribute': 'data-ytce-role-label' in t, 'ready_post_marker': 'r42ed_role_colour_cleanup' in t}; print(json.dumps(checks, indent=2)); raise SystemExit(0 if all(checks.values()) else 2)"
if errorlevel 1 exit /b %ERRORLEVEL%
echo [R42ED] Checking R42DW payload metadata hook...
call tools\webview2_source_role_editor_native\_r42ed_python.cmd -c "from pathlib import Path; import json; t=Path('profile_media_archive_role_payload_r42dw.py').read_text(encoding='utf-8', errors='replace'); checks={'metadata_func':'_r42ed_payload_overlay_metadata' in t, 'payload_key':'role_comprehension_matrix' in t, 'colour_key':'role_colour_theme' in t, 'adapter_key':'adapter_guard_matrix' in t}; print(json.dumps(checks, indent=2)); raise SystemExit(0 if all(checks.values()) else 2)"
if errorlevel 1 exit /b %ERRORLEVEL%
echo [R42ED] Building native WebView2 helper after colour cleanup source change...
dotnet build tools\webview2_source_role_editor_native\YTCE.NativeSourceRoleEditor.csproj -c Release
if errorlevel 1 exit /b %ERRORLEVEL%
echo [DONE] R42ED smoke/build passed without opening GUI/WebView2/archive.ph.
