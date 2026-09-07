@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%" || exit /b 1
echo [R42DU] Probing archive visible material/source-role fixes...
call tools\webview2_source_role_editor_native\_r42du_python.cmd tools\webview2_source_role_editor_native\probe_r42du_archive_visible_material_source_roles.py || exit /b 1
endlocal
