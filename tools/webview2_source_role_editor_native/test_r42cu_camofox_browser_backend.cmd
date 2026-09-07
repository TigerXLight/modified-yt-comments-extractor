@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."
set "OUT=profile_media_live_captures\r42cu_camofox_browser_manual_test"
if exist "%OUT%" rmdir /s /q "%OUT%"
mkdir "%OUT%" >nul 2>&1
set "PY=C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe"
if not exist "%PY%" set "PY=python"
echo [R42CU] Running managed camofox-browser backend manual test...
echo [R42CU] Output: %OUT%
"%PY%" "profile_media_camofox_browser_server_backend_r42cu.py" --url "https://archive.ph/6mr3C" --title "People shout seagull eater Metro News" --row-id "manual-archive-6mr3c" --output-dir "%OUT%" --timeout 180
set "RC=%ERRORLEVEL%"
echo [R42CU] Exit code: %RC%
dir /a "%OUT%"
exit /b %RC%
