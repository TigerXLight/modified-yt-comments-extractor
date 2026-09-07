@echo off
setlocal EnableExtensions
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%..\.." >nul || exit /b 1
set "ROOT=%CD%"
popd >nul
set "OUT=%ROOT%\profile_media_live_captures\link_source_role_webview_overlay"
set "BUILDOUT=%OUT%\r42ba_native_editor_build"
set "EXE=%BUILDOUT%\YTCE.NativeSourceRoleEditor.R42BA.exe"
set "CMD_DIR=%OUT%\r42ba_native_editor_server"
set "LOG=%OUT%\selected_link_source_role_native_webview2_launch.log"
if not exist "%EXE%" (
  echo ERROR: Missing %EXE%
  echo Build first: tools\webview2_source_role_editor_native\build_r42ai_native_source_role_editor.cmd
  exit /b 1
)
if not exist "%CMD_DIR%" mkdir "%CMD_DIR%" >nul 2>nul
echo Starting R42BA warm native WebView2 source-role editor server...
echo Log: %LOG%
start "" /B "%EXE%" --server --root "%ROOT%" --udf "%LOCALAPPDATA%\YTCE\WebView2SourceRoleEditor" --log "%LOG%" --command-dir "%CMD_DIR%"
echo Started. Keep main.py open and click a source edit icon after server_ready appears in the log.
