@echo off
setlocal
set "PY=C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" %*
exit /b %ERRORLEVEL%
