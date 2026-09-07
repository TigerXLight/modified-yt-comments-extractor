@echo off
setlocal
set "PY=C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe"
if exist "%PY%" goto run
for %%P in (python.exe py.exe) do (
  for /f "delims=" %%X in ('where %%P 2^>nul') do (
    set "PY=%%X"
    goto run
  )
)
echo [FAIL] Python not found.
exit /b 1
:run
"%PY%" %*
