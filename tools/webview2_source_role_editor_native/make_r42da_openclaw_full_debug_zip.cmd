@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."
echo [R42DA] Creating combined OpenClaw debug/reference ZIP...
python profile_media_openclaw_all_reference_layer_r42da.py --debug-zip
if errorlevel 1 (
  echo [FAIL] R42DA debug ZIP build failed.
  exit /b 1
)
echo [DONE] R42DA debug ZIP build complete.
endlocal
