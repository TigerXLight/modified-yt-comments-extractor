@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "ONE=%USERPROFILE%\Downloads\r42dw_archive_only_6mr3c.txt"
> "%ONE%" echo https://archive.ph/6mr3C
set "YTCE_R42DU_TEXT_PAINT_STYLE=recolor"
cd /d "%ROOT%" || exit /b 1
call tools\webview2_source_role_editor_native\reset_r42dw_native_webview2_server.cmd
echo [R42DW] One-link archive.ph test file:
echo %ONE%
echo [R42DW] Launching app with post-capture role-payload refresh + recolour mode enabled...
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe main.py
endlocal
