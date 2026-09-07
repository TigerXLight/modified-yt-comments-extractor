@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."
set "PLUGIN=%CD%\tools\camofox_browser_backend_r42cu\jo_inc_camofox_browser"
for /f "delims=" %%I in ('where openclaw 2^>nul') do if not defined OPENCLAW_CMD set "OPENCLAW_CMD=%%I"
if not defined OPENCLAW_CMD set "OPENCLAW_CMD=%APPDATA%\npm\openclaw.cmd"
if not exist "%OPENCLAW_CMD%" (
  echo [FAIL] OpenClaw CLI not found.
  exit /b 1
)
echo [R42DA] Accepting/re-accepting camofox-browser local plugin capabilities...
echo [R42DA] OpenClaw: "%OPENCLAW_CMD%"
echo [R42DA] Plugin: "%PLUGIN%"
call "%OPENCLAW_CMD%" plugins install -l "%PLUGIN%" --force --accept-capabilities
if errorlevel 1 exit /b 1
call "%OPENCLAW_CMD%" plugins enable camofox-browser --accept-capabilities
if errorlevel 1 exit /b 1
echo [DONE] camofox-browser local plugin installed/enabled with capability consent.
endlocal
