@echo off
setlocal
cd /d "%~dp0\..\.."
if not exist "profile_media_openclaw_full_suite_installer_r42dc.py" (
  echo [FAIL] Could not locate project root from script path.
  exit /b 1
)
if /I not "%YTCE_R42DC_ENABLE_ALL_INSTALLED_OPENCLAW%"=="YES" (
  echo [FAIL] This command enables currently installed disabled OpenClaw plugins.
  echo        Re-run with: set YTCE_R42DC_ENABLE_ALL_INSTALLED_OPENCLAW=YES
  exit /b 2
)
echo [R42DC] Enabling all currently installed disabled OpenClaw plugins with capability acceptance...
python profile_media_openclaw_full_suite_installer_r42dc.py enable-installed
endlocal
