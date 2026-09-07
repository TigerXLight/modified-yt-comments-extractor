@echo off
setlocal
cd /d "%~dp0\..\.."
if not exist "profile_media_openclaw_full_suite_installer_r42dd.py" (
  echo [FAIL] Could not locate project root from script path.
  exit /b 1
)
echo [R42DD] Building post-enable/install OpenClaw full-suite reference ZIP...
call "%~dp0\_r42dd_python.cmd" profile_media_openclaw_full_suite_installer_r42dd.py build-reference-zip
exit /b %ERRORLEVEL%
