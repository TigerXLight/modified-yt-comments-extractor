@echo off
setlocal
set "NATIVEPY=C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe"
if exist "%NATIVEPY%" (
  "%NATIVEPY%" %*
  exit /b %ERRORLEVEL%
)
py -3.11 %*
exit /b %ERRORLEVEL%
