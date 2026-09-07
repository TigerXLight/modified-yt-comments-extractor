@echo off
setlocal EnableExtensions
cd /d "%~dp0..\.."
set "ROOT=%CD%"
set "PY=C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe"
if not exist "%PY%" set "PY=python"
echo [R42CZ] Building OpenClaw backup/reference layer...
"%PY%" "%ROOT%\profile_media_openclaw_backup_reference_layer_r42cz.py" --root "%ROOT%" --copy-to-downloads
exit /b %ERRORLEVEL%
