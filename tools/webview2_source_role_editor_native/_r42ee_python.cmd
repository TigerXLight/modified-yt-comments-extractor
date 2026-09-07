@echo off
setlocal
set "ROOT=%~dp0..\.."
set "PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if exist "%PY%" (
  "%PY%" %*
  exit /b %ERRORLEVEL%
)
py -3 %*
if not errorlevel 9009 exit /b %ERRORLEVEL%
python %*
exit /b %ERRORLEVEL%
