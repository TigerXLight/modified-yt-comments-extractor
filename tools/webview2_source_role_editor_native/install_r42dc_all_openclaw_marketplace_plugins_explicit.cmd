@echo off
setlocal
cd /d "%~dp0\..\.."
if not exist "profile_media_openclaw_full_suite_installer_r42dc.py" (
  echo [FAIL] Could not locate project root from script path.
  exit /b 1
)
if /I not "%YTCE_R42DC_INSTALL_ALL_OPENCLAW_MARKETPLACE%"=="YES" (
  echo [FAIL] This command attempts to install all marketplace plugin specs captured in R42DA/R42DB.
  echo        Re-run with: set YTCE_R42DC_INSTALL_ALL_OPENCLAW_MARKETPLACE=YES
  echo        Optional: set YTCE_R42DC_BUCKET=A_SOURCE_CAPTURE_BROWSER_WEB
  echo        Optional: set YTCE_R42DC_INSTALL_LIMIT=10
  exit /b 2
)
echo [R42DC] Installing all captured OpenClaw marketplace plugins with capability acceptance...
python profile_media_openclaw_full_suite_installer_r42dc.py install-marketplace
endlocal
