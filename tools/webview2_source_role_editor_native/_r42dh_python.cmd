@echo off
setlocal
set "PY_NATIVE=C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe"
if exist "%PY_NATIVE%" (
  "%PY_NATIVE%" %*
  exit /b %ERRORLEVEL%
)
py -3.11 %*
if not errorlevel 9009 exit /b %ERRORLEVEL%
python %*
exit /b %ERRORLEVEL%
