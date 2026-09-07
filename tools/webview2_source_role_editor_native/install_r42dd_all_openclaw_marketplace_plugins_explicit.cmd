@echo off
setlocal
cd /d "%~dp0\..\.."
if not exist "profile_media_openclaw_full_suite_installer_r42dd.py" (
  echo [FAIL] Could not locate project root from script path.
  exit /b 1
)
if /I "%~1"=="YES" goto run
if /I "%YTCE_R42DD_INSTALL_ALL_OPENCLAW_MARKETPLACE%"=="YES" goto run
if /I "%YTCE_R42DC_INSTALL_ALL_OPENCLAW_MARKETPLACE%"=="YES" goto run
echo [FAIL] This explicitly installs captured OpenClaw marketplace plugin specs.
echo        Run exactly:
echo        tools\webview2_source_role_editor_native\install_r42dd_all_openclaw_marketplace_plugins_explicit.cmd YES
echo        Optional before command: set YTCE_R42DD_BUCKET=A_SOURCE_CAPTURE_BROWSER_WEB
echo        Optional before command: set YTCE_R42DD_INSTALL_LIMIT=10
exit /b 2
:run
echo [R42DD] Installing captured OpenClaw marketplace plugins with capability acceptance...
call "%~dp0\_r42dd_python.cmd" profile_media_openclaw_full_suite_installer_r42dd.py install-marketplace YES
exit /b %ERRORLEVEL%
