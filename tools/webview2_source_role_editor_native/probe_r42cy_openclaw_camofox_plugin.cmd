@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0..\.."
set "ROOT=%CD%"
set "OUT=%ROOT%\profile_media_live_captures\r42cy_openclaw_camofox"
mkdir "%OUT%" 2>nul
set "OPENCLAW_CMD="
for /f "usebackq delims=" %%O in (`where openclaw 2^>nul`) do (
  if /i "%%~xO"==".cmd" if not defined OPENCLAW_CMD set "OPENCLAW_CMD=%%O"
)
if not defined OPENCLAW_CMD for /f "usebackq delims=" %%O in (`where openclaw 2^>nul`) do if not defined OPENCLAW_CMD set "OPENCLAW_CMD=%%O"

echo [R42CY] Probe root: "%ROOT%"
if not defined OPENCLAW_CMD (
  echo [FAIL] OpenClaw CLI not found on PATH.
  exit /b 2
)
echo [R42CY] Using OpenClaw command: "%OPENCLAW_CMD%"
call "%OPENCLAW_CMD%" --version > "%OUT%\probe_openclaw_version.txt" 2>&1
type "%OUT%\probe_openclaw_version.txt"
call "%OPENCLAW_CMD%" plugins list --json > "%OUT%\probe_plugins_list.json" 2> "%OUT%\probe_plugins_list.stderr.txt"
call "%OPENCLAW_CMD%" plugins inspect camofox-browser --json > "%OUT%\probe_camofox_inspect_cold.json" 2> "%OUT%\probe_camofox_inspect_cold.stderr.txt"
call "%OPENCLAW_CMD%" plugins inspect camofox-browser --runtime --json > "%OUT%\probe_camofox_inspect_runtime.json" 2> "%OUT%\probe_camofox_inspect_runtime.stderr.txt"
call "%OPENCLAW_CMD%" gateway status --json > "%OUT%\probe_gateway_status.json" 2> "%OUT%\probe_gateway_status.stderr.txt"
"C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe" "%ROOT%\profile_media_openclaw_plugin_inventory_r42cy.py" --output-dir "%OUT%" > "%OUT%\probe_inventory_stdout.json" 2> "%OUT%\probe_inventory_stderr.txt"
if exist "%OUT%\r42cy_openclaw_inventory_summary.txt" type "%OUT%\r42cy_openclaw_inventory_summary.txt"
echo [DONE] R42CY OpenClaw/Camofox probe output: "%OUT%"
exit /b 0
