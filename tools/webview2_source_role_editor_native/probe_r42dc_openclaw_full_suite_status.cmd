@echo off
setlocal
cd /d "%~dp0\..\.."
if not exist "profile_media_openclaw_full_suite_installer_r42dc.py" (
  echo [FAIL] Could not locate project root from script path.
  exit /b 1
)
echo [R42DC] Probing OpenClaw full-suite status...
python profile_media_openclaw_full_suite_installer_r42dc.py probe
endlocal
