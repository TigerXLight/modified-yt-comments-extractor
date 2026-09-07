@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
echo [R42DW] Resetting stale native WebView2 warm helper/server...
taskkill /F /IM YTCE.NativeSourceRoleEditor.R42CR.exe /T >nul 2>nul
set "SERVER=%ROOT%\profile_media_live_captures\link_source_role_webview_overlay\r42cr_native_editor_server"
if exist "%SERVER%" (
  del /q "%SERVER%\r42cr_server_ready.json" >nul 2>nul
  del /q "%SERVER%\r42cr_server_starting.json" >nul 2>nul
  del /q "%SERVER%\command_*.json" >nul 2>nul
  del /q "%SERVER%\pending_*.tmp" >nul 2>nul
  del /q "%SERVER%\r42cr_command_write.lock" >nul 2>nul
  del /q "%SERVER%\r42cr_last_command_guard.json" >nul 2>nul
)
echo [DONE] R42DW native WebView2 server reset complete.
endlocal
