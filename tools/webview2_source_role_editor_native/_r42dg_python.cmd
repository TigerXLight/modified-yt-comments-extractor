@echo off
setlocal
set "_PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if exist "%_PY%" (
  "%_PY%" %*
  exit /b %ERRORLEVEL%
)
where py.exe >nul 2>nul
if not errorlevel 1 (
  py -3.11 %*
  exit /b %ERRORLEVEL%
)
python %*
exit /b %ERRORLEVEL%
