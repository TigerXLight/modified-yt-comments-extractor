@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "PY=C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe"
if defined PYTHONPATH (
  set "PYTHONPATH=%ROOT%;%PYTHONPATH%"
) else (
  set "PYTHONPATH=%ROOT%"
)
cd /d "%ROOT%" || exit /b 1
if exist "%PY%" (
  "%PY%" %*
) else (
  python %*
)
endlocal
