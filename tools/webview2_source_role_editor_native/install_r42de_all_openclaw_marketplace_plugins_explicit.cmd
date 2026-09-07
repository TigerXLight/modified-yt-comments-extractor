@echo off
setlocal
if /I not "%~1"=="YES" (
  echo [FAIL] This command installs ALL captured OpenClaw marketplace plugin specs.
  echo        Re-run exactly with: install_r42de_all_openclaw_marketplace_plugins_explicit.cmd YES
  exit /b 2
)
cd /d "%~dp0..\.." >nul 2>nul
cd /d "%CD%"
rem R42DE deliberately clears old bucket/limit variables from R42DC/R42DD.
set "YTCE_R42DC_BUCKET="
set "YTCE_R42DD_BUCKET="
set "YTCE_R42DC_INSTALL_LIMIT="
set "YTCE_R42DD_INSTALL_LIMIT="
set "YTCE_R42DE_INSTALL_ALL_OPENCLAW_MARKETPLACE=YES"
echo [R42DE] Installing ALL captured OpenClaw marketplace plugin specs. No inherited bucket filter.
call tools\webview2_source_role_editor_native\_r42de_python.cmd profile_media_openclaw_full_suite_installer_r42de.py install-marketplace-all YES
exit /b %ERRORLEVEL%
