@echo off
setlocal
set "PY=C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe"
if exist "%PY%" goto run
set "PY=python"
:run
"%PY%" %*
