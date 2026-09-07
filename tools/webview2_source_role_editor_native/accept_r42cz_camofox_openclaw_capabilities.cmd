@echo off
setlocal EnableExtensions
cd /d "%~dp0..\.."
set "ROOT=%CD%"
set "PLUGIN=%ROOT%\tools\camofox_browser_backend_r42cu\jo_inc_camofox_browser"
set "OUT=%ROOT%\profile_media_live_captures\r42cz_openclaw_reference_layer_accept"
mkdir "%OUT%" 2>nul
where openclaw > "%OUT%\where_openclaw.txt" 2> "%OUT%\where_openclaw.stderr.txt"
if errorlevel 1 (
  echo [FAIL] openclaw was not found on PATH.
  exit /b 2
)
for /f "delims=" %%O in ('where openclaw ^| findstr /I "openclaw.cmd"') do if not defined OPENCLAW set "OPENCLAW=%%O"
if not defined OPENCLAW set "OPENCLAW=openclaw"
echo [R42CZ] Using OpenClaw command: "%OPENCLAW%"
call "%OPENCLAW%" --version > "%OUT%\openclaw_version.txt" 2> "%OUT%\openclaw_version.stderr.txt"
echo [R42CZ] Installing linked local camofox-browser plugin with explicit capability acceptance...
call "%OPENCLAW%" plugins install -l "%PLUGIN%" --force --accept-capabilities > "%OUT%\plugins_install_link_accept.stdout.txt" 2> "%OUT%\plugins_install_link_accept.stderr.txt"
if errorlevel 1 (
  echo [FAIL] OpenClaw plugins install -l --force --accept-capabilities failed.
  echo [INFO] See: "%OUT%\plugins_install_link_accept.stderr.txt"
  exit /b 3
)
echo [R42CZ] Enabling camofox-browser with explicit capability acceptance...
call "%OPENCLAW%" plugins enable camofox-browser --accept-capabilities > "%OUT%\plugins_enable_accept.stdout.txt" 2> "%OUT%\plugins_enable_accept.stderr.txt"
if errorlevel 1 (
  echo [WARN] OpenClaw plugins enable returned non-zero; inspect stderr. Install may already have enabled it.
)
call "%OPENCLAW%" plugins inspect camofox-browser --json > "%OUT%\plugins_inspect_camofox_cold.json" 2> "%OUT%\plugins_inspect_camofox_cold.stderr.txt"
call "%OPENCLAW%" plugins inspect camofox-browser --runtime --json > "%OUT%\plugins_inspect_camofox_runtime.json" 2> "%OUT%\plugins_inspect_camofox_runtime.stderr.txt"
echo [DONE] Capability-accepted camofox-browser plugin command completed.
echo [INFO] Output: "%OUT%"
exit /b 0
