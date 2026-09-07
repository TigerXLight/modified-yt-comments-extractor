@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%" || exit /b 1
echo [R42DU] Running archive visible-material/source-role smoke tests...
call tools\webview2_source_role_editor_native\_r42du_python.cmd profile_media_archive_material_visible_roles_r42du_test.py || exit /b 1
echo [R42DU] Building native WebView2 helper with material-over-challenge fix...
taskkill /F /IM YTCE.NativeSourceRoleEditor.R42CR.exe >nul 2>nul
pushd tools\webview2_source_role_editor_native || exit /b 1
dotnet restore YTCE.NativeSourceRoleEditor.csproj || exit /b 1
dotnet publish YTCE.NativeSourceRoleEditor.csproj -c Release -o "%ROOT%\profile_media_live_captures\link_source_role_webview_overlay\r42cr_native_editor_build" --self-contained false /p:UseAppHost=true || exit /b 1
popd
echo [DONE] R42DU smoke/build passed.
endlocal
