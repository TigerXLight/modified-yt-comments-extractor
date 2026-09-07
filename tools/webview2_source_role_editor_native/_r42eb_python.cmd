@echo off
setlocal
set "ROOT=%~dp0..\.."
set "PY=C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe"
if exist "%PY%" (
  "%PY%" %*
) else (
  python %*
)
exit /b %ERRORLEVEL%
