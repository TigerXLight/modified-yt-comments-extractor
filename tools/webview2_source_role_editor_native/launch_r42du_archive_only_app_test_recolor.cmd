@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "ONE=%USERPROFILE%\Downloads\r42du_archive_only_6mr3c.txt"
> "%ONE%" echo https://archive.ph/6mr3C
set "YTCE_R42DU_TEXT_PAINT_STYLE=recolor"
cd /d "%ROOT%" || exit /b 1
echo [R42DU] One-link archive.ph test file:
echo %ONE%
echo [R42DU] Launching app with text recolour style enabled...
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe main.py
endlocal
