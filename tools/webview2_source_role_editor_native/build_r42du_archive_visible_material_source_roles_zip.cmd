@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%" || exit /b 1
echo [R42DU] Building archive visible material/source-role reference ZIP...
call tools\webview2_source_role_editor_native\probe_r42du_archive_visible_material_source_roles.cmd || exit /b 1
call tools\webview2_source_role_editor_native\_r42du_python.cmd tools\webview2_source_role_editor_native\build_r42du_archive_visible_material_source_roles_zip.py || exit /b 1
endlocal
