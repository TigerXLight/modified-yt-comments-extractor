@echo off
setlocal EnableExtensions
cd /d "%~dp0..\.." || exit /b 1
set "PY=C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe"
if not exist "%PY%" set "PY=python"
for /f "tokens=1-4 delims=/-. " %%a in ("%date%") do set "D=%%d%%b%%c"
for /f "tokens=1-4 delims=:. " %%a in ("%time%") do set "T=%%a%%b%%c"
set "T=%T: =0%"
set "STAMP=%D%_%T%"
set "OUT=%USERPROFILE%\Downloads\r42cm_archive_material_test_audit_%STAMP%.txt"
echo Writing audit to: %OUT%
"%PY%" "%~dp0r42cm_archive_material_audit.py" --root "%CD%" --out "%OUT%"
if errorlevel 1 (
  echo Audit failed.
  exit /b 1
)
echo Done. Upload this audit if needed:
echo %OUT%
