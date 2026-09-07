@echo off
setlocal
set "PY311=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if exist "%PY311%" (
  "%PY311%" %*
  exit /b %ERRORLEVEL%
)
py -3.11 %*
if not errorlevel 9009 exit /b %ERRORLEVEL%
python %*
exit /b %ERRORLEVEL%
