@echo off
setlocal
set "PY=C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe"
if exist "%PY%" (
  "%PY%" %*
) else (
  py -3 %*
)
endlocal
