@echo off
setlocal
cd /d "%~dp0\..\.."
if not exist "profile_media_openclaw_full_suite_installer_r42dd.py" (
  echo [FAIL] Could not locate project root from script path.
  exit /b 1
)
if /I "%~1"=="YES" goto run
if /I "%YTCE_R42DD_ENABLE_ALL_INSTALLED_OPENCLAW%"=="YES" goto run
if /I "%YTCE_R42DC_ENABLE_ALL_INSTALLED_OPENCLAW%"=="YES" goto run
echo [FAIL] This explicitly enables currently installed disabled OpenClaw plugins.
echo        Run exactly:
echo        tools\webview2_source_role_editor_native\enable_r42dd_all_installed_openclaw_plugins_explicit.cmd YES
exit /b 2
:run
echo [R42DD] Enabling all currently installed disabled OpenClaw plugins with capability acceptance...
call "%~dp0\_r42dd_python.cmd" profile_media_openclaw_full_suite_installer_r42dd.py enable-installed YES
exit /b %ERRORLEVEL%
