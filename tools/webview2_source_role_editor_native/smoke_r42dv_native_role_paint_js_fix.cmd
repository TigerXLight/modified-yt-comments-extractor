@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%" || exit /b 1
echo [R42DV] Running native role-paint JavaScript/counter smoke test...
call tools\webview2_source_role_editor_native\_r42dv_python.cmd profile_media_native_role_paint_js_r42dv_test.py || exit /b 1
echo [R42DV] Rebuilding native WebView2 helper with JS syntax fix...
taskkill /F /IM YTCE.NativeSourceRoleEditor.R42CR.exe >nul 2>nul
pushd tools\webview2_source_role_editor_native || exit /b 1
dotnet restore YTCE.NativeSourceRoleEditor.csproj || exit /b 1
dotnet publish YTCE.NativeSourceRoleEditor.csproj -c Release -o "%ROOT%\profile_media_live_captures\link_source_role_webview_overlay\r42cr_native_editor_build" --self-contained false /p:UseAppHost=true || exit /b 1
popd
echo [DONE] R42DV smoke/build passed.
endlocal
