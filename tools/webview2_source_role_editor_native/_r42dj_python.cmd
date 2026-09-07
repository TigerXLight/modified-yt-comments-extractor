@echo off
setlocal
set "PY=C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe"
if exist "%PY%" (
  "%PY%" %*
  exit /b %ERRORLEVEL%
)
where py >nul 2>nul
if not errorlevel 1 (
  py -3.11 %*
  exit /b %ERRORLEVEL%
)
python %*
exit /b %ERRORLEVEL%
