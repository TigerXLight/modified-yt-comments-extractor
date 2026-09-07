@echo off
setlocal
if /I not "%~1"=="YES" (
  echo [FAIL] Usage: install_r42de_openclaw_marketplace_plugins_limited_explicit.cmd YES 25
  exit /b 2
)
if not "%~2"=="" set "YTCE_R42DE_INSTALL_LIMIT=%~2"
cd /d "%~dp0..\.." >nul 2>nul
cd /d "%CD%"
set "YTCE_R42DC_BUCKET="
set "YTCE_R42DD_BUCKET="
set "YTCE_R42DC_INSTALL_LIMIT="
set "YTCE_R42DD_INSTALL_LIMIT="
set "YTCE_R42DE_INSTALL_ALL_OPENCLAW_MARKETPLACE=YES"
echo [R42DE] Installing captured marketplace plugins with optional limit %YTCE_R42DE_INSTALL_LIMIT%.
call tools\webview2_source_role_editor_native\_r42de_python.cmd profile_media_openclaw_full_suite_installer_r42de.py install-marketplace-all YES
exit /b %ERRORLEVEL%
