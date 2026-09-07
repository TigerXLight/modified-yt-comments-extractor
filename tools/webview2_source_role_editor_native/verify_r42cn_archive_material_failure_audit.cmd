@echo off
setlocal EnableExtensions
cd /d "%~dp0..\.." || exit /b 1
set "PY=C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe"
if not exist "%PY%" set "PY=python"
for /f "tokens=1-4 delims=/-. " %%a in ("%date%") do set "D=%%d%%b%%c"
for /f "tokens=1-4 delims=:. " %%a in ("%time%") do set "T=%%a%%b%%c"
set "T=%T: =0%"
set "STAMP=%D%_%T%"
set "OUT=%USERPROFILE%\Downloads\r42cn_archive_material_failure_audit_%STAMP%.txt"
set "ZIP=%USERPROFILE%\Downloads\r42cn_archive_material_failure_deep_debug_%STAMP%.zip"
echo Writing audit to: %OUT%
"%PY%" "%~dp0r42cn_archive_material_failure_audit.py" --root "%CD%" --out "%OUT%" --make-zip "%ZIP%"
if errorlevel 1 (
  echo Audit failed.
  exit /b 1
)
echo Done. Upload if needed:
echo %OUT%
echo %ZIP%
