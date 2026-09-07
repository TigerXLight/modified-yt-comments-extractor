@echo off
setlocal
cd /d "%~dp0..\.."
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PY=C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" %*
exit /b %ERRORLEVEL%
