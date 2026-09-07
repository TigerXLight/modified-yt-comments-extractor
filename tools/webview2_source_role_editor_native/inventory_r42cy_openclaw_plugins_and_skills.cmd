@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0..\.."
set "ROOT=%CD%"
set "OUT=%ROOT%\profile_media_live_captures\r42cy_openclaw_inventory"
mkdir "%OUT%" 2>nul
set "OPENCLAW_CMD="
for /f "usebackq delims=" %%O in (`where openclaw 2^>nul`) do (
  if /i "%%~xO"==".cmd" if not defined OPENCLAW_CMD set "OPENCLAW_CMD=%%O"
)
if not defined OPENCLAW_CMD for /f "usebackq delims=" %%O in (`where openclaw 2^>nul`) do if not defined OPENCLAW_CMD set "OPENCLAW_CMD=%%O"
if not defined OPENCLAW_CMD (
  echo [FAIL] OpenClaw CLI not found.
  exit /b 2
)
echo [R42CY] Inventorying OpenClaw plugins/skills. Output: "%OUT%"
call "%OPENCLAW_CMD%" --version > "%OUT%\openclaw_version.txt" 2>&1
call "%OPENCLAW_CMD%" plugins list --json > "%OUT%\plugins_list.json" 2> "%OUT%\plugins_list.stderr.txt"
call "%OPENCLAW_CMD%" skills list --json > "%OUT%\skills_list.json" 2> "%OUT%\skills_list.stderr.txt"
call "%OPENCLAW_CMD%" skills check --json > "%OUT%\skills_check.json" 2> "%OUT%\skills_check.stderr.txt"
call "%OPENCLAW_CMD%" doctor > "%OUT%\doctor.txt" 2> "%OUT%\doctor.stderr.txt"
"C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe" "%ROOT%\profile_media_openclaw_plugin_inventory_r42cy.py" --output-dir "%OUT%" > "%OUT%\inventory_stdout.json" 2> "%OUT%\inventory_stderr.txt"
if exist "%OUT%\r42cy_openclaw_inventory_summary.txt" type "%OUT%\r42cy_openclaw_inventory_summary.txt"
echo [DONE] Inventory complete: "%OUT%"
exit /b 0
