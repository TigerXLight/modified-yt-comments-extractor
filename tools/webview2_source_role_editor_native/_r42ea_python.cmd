@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "PY=C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe"
if not exist "%PY%" set "PY=python"
set "PYTHONPATH=%ROOT%;%PYTHONPATH%"
"%PY%" %*
exit /b %ERRORLEVEL%
