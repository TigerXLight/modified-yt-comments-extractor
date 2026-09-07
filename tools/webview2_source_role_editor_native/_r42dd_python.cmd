@echo off
set "YTCE_NATIVE_PY=C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe"
if exist "%YTCE_NATIVE_PY%" (
  "%YTCE_NATIVE_PY%" %*
  exit /b %ERRORLEVEL%
)
py -3.11 %*
if not errorlevel 9009 exit /b %ERRORLEVEL%
py -3 %*
if not errorlevel 9009 exit /b %ERRORLEVEL%
python %*
exit /b %ERRORLEVEL%
