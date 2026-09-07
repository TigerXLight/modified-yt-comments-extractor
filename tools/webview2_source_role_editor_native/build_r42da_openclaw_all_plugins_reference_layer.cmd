@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."
echo [R42DA] Building OpenClaw all-plugin/skill backup reference layer...
python profile_media_openclaw_all_reference_layer_r42da.py
if errorlevel 1 (
  echo [FAIL] R42DA reference layer build failed.
  exit /b 1
)
echo [DONE] R42DA reference layer build complete.
endlocal
