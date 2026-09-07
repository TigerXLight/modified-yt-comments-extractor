@echo off
setlocal
set "PY=C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe"
if exist "%PY%" (
  "%PY%" %*
  exit /b %ERRORLEVEL%
)
py -3.11 %*
if %ERRORLEVEL% EQU 0 exit /b 0
py -3 %*
if %ERRORLEVEL% EQU 0 exit /b 0
python %*
exit /b %ERRORLEVEL%
