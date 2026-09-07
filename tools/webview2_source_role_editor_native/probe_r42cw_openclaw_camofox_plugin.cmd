@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0..\.."
set "ROOT=%CD%"
set "PLUGIN=%ROOT%\tools\camofox_browser_backend_r42cu\jo_inc_camofox_browser"
set "OUT=%ROOT%\profile_media_live_captures\r42cv_openclaw_camofox"
mkdir "%OUT%" 2>nul

rem R42CW hotfix: when a .cmd file invokes another .cmd file, it must use CALL.
rem npm installs OpenClaw as openclaw.cmd on Windows. Without CALL, the parent script
rem transfers control to openclaw.cmd and silently never resumes after redirected output.

set "OPENCLAW_CMD="
for /f "usebackq delims=" %%O in (`where openclaw 2^>nul`) do (
  if /i "%%~xO"==".cmd" if not defined OPENCLAW_CMD set "OPENCLAW_CMD=%%O"
)
if not defined OPENCLAW_CMD (
  for /f "usebackq delims=" %%O in (`where openclaw 2^>nul`) do (
    if not defined OPENCLAW_CMD set "OPENCLAW_CMD=%%O"
  )
)

where openclaw > "%OUT%\where_openclaw.txt" 2>&1
if errorlevel 1 (
  echo [WARN] OpenClaw CLI was not found on PATH.
  echo [INFO] Output: "%OUT%"
  exit /b 2
)
if not defined OPENCLAW_CMD (
  echo [FAIL] where openclaw succeeded but no .cmd/executable path was captured.
  echo See "%OUT%\where_openclaw.txt"
  exit /b 3
)

echo [R42CW] Using OpenClaw command: "%OPENCLAW_CMD%"
call "%OPENCLAW_CMD%" --version > "%OUT%\openclaw_version.txt" 2>&1
if errorlevel 1 (
  echo [FAIL] OpenClaw --version failed. See "%OUT%\openclaw_version.txt".
  exit /b 4
)

call "%OPENCLAW_CMD%" config get gateway.mode > "%OUT%\openclaw_gateway_mode.txt" 2> "%OUT%\openclaw_gateway_mode.stderr.txt"
call "%OPENCLAW_CMD%" plugins list --json > "%OUT%\openclaw_plugins_list.json" 2> "%OUT%\openclaw_plugins_list.stderr.txt"
call "%OPENCLAW_CMD%" plugins inspect camofox-browser --runtime --json > "%OUT%\openclaw_camofox_inspect_runtime.json" 2> "%OUT%\openclaw_camofox_inspect_runtime.stderr.txt"
call "%OPENCLAW_CMD%" camofox status > "%OUT%\openclaw_camofox_status.txt" 2>&1
"C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe" "%ROOT%\profile_media_openclaw_camofox_bridge_r42cv.py" > "%OUT%\python_inventory_stdout.json" 2> "%OUT%\python_inventory_stderr.txt"

echo [DONE] R42CW OpenClaw/Camofox probe output: "%OUT%"
exit /b 0
