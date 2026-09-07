@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "OUT=%ROOT%\profile_media_live_captures\link_source_role_webview_overlay"
set "EXE=%OUT%\r42bi_native_editor_build\YTCE.NativeSourceRoleEditor.R42BI.exe"
if not exist "%EXE%" (
  echo Missing helper: %EXE%
  echo Run tools\webview2_source_role_editor_native\build_r42ai_native_source_role_editor.cmd first.
  exit /b 1
)
start "YTCE R42BI warm source-role editor" "%EXE%" --server --root "%ROOT%" --udf "%LOCALAPPDATA%\YTCE\WebView2SourceRoleEditor" --log "%OUT%\selected_link_source_role_native_webview2_launch.log" --command-dir "%OUT%\r42bi_native_editor_server"
endlocal
