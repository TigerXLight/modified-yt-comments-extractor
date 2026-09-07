@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0..\.."
set "ROOT=%CD%"
set "PLUGIN=%ROOT%\tools\camofox_browser_backend_r42cu\jo_inc_camofox_browser"
set "OUT=%ROOT%\profile_media_live_captures\r42cx_openclaw_camofox"
mkdir "%OUT%" 2>nul

echo [R42CX] Probe root: "%ROOT%"
where openclaw > "%OUT%\where_openclaw.txt" 2>&1
if errorlevel 1 (
  echo [FAIL] OpenClaw CLI not found.
  exit /b 2
)
for /f "usebackq delims=" %%O in (`where openclaw 2^>nul`) do (
  if /i "%%~xO"==".cmd" if not defined OPENCLAW_CMD set "OPENCLAW_CMD=%%O"
)
if not defined OPENCLAW_CMD for /f "usebackq delims=" %%O in (`where openclaw 2^>nul`) do if not defined OPENCLAW_CMD set "OPENCLAW_CMD=%%O"
echo [R42CX] Using OpenClaw command: "%OPENCLAW_CMD%"
call "%OPENCLAW_CMD%" --version > "%OUT%\openclaw_version.txt" 2>&1
type "%OUT%\openclaw_version.txt"

call "%OPENCLAW_CMD%" config get gateway.mode > "%OUT%\openclaw_gateway_mode.txt" 2> "%OUT%\openclaw_gateway_mode.stderr.txt"
call "%OPENCLAW_CMD%" plugins list --json > "%OUT%\openclaw_plugins_list.json" 2> "%OUT%\openclaw_plugins_list.stderr.txt"
call "%OPENCLAW_CMD%" plugins inspect camofox-browser --json > "%OUT%\openclaw_camofox_inspect_cold.json" 2> "%OUT%\openclaw_camofox_inspect_cold.stderr.txt"
call "%OPENCLAW_CMD%" plugins inspect camofox-browser --runtime --json > "%OUT%\openclaw_camofox_inspect_runtime.json" 2> "%OUT%\openclaw_camofox_inspect_runtime.stderr.txt"
call "%OPENCLAW_CMD%" gateway status --json > "%OUT%\openclaw_gateway_status.json" 2> "%OUT%\openclaw_gateway_status.stderr.txt"
"C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe" "%ROOT%\profile_media_openclaw_camofox_bridge_r42cv.py" > "%OUT%\python_inventory_stdout.json" 2> "%OUT%\python_inventory_stderr.txt"

echo [DONE] R42CX OpenClaw/Camofox probe output: "%OUT%"
exit /b 0
