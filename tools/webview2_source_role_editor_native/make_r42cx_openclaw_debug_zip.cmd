@echo off
setlocal EnableExtensions
cd /d "%~dp0..\.."
set "ROOT=%CD%"
set "STAMP=%DATE:~-4%%DATE:~3,2%%DATE:~0,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
set "STAMP=%STAMP: =0%"
set "OUTDIR=%ROOT%\profile_media_live_captures\r42cx_openclaw_camofox"
set "ZIP=%ROOT%\profile_media_live_captures\r42cx_openclaw_camofox_debug_%STAMP%.zip"
if not exist "%OUTDIR%" (
  echo [FAIL] Output folder not found: "%OUTDIR%"
  exit /b 2
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -LiteralPath '%OUTDIR%\*' -DestinationPath '%ZIP%' -Force"
echo [DONE] Created: "%ZIP%"
exit /b 0
