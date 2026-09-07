@echo off
setlocal
cd /d "%~dp0\..\.."
if not exist "profile_media_openclaw_full_suite_installer_r42dd.py" (
  echo [FAIL] Could not locate project root from script path.
  exit /b 1
)
echo [R42DD] Probing OpenClaw full-suite status with UTF-8-safe capture...
call "%~dp0\_r42dd_python.cmd" profile_media_openclaw_full_suite_installer_r42dd.py probe
exit /b %ERRORLEVEL%
