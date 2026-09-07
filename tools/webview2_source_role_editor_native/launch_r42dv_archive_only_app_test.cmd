@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "ONE=%USERPROFILE%\Downloads\r42dv_archive_only_6mr3c.txt"
> "%ONE%" echo https://archive.ph/6mr3C
cd /d "%ROOT%" || exit /b 1
echo [R42DV] One-link archive.ph test file:
echo %ONE%
echo [R42DV] Launching app after native role-paint JS fix...
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe main.py
endlocal
