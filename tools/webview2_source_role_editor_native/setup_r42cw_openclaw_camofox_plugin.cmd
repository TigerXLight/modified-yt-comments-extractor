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
  echo [FAIL] OpenClaw CLI was not found on PATH.
  echo Install OpenClaw separately, then rerun this command.
  echo Project plugin path prepared: "%PLUGIN%"
  exit /b 2
)
if not exist "%PLUGIN%\openclaw.plugin.json" (
  echo [FAIL] Bundled camofox-browser OpenClaw plugin manifest not found:
  echo        "%PLUGIN%\openclaw.plugin.json"
  exit /b 3
)
if not defined OPENCLAW_CMD (
  echo [FAIL] where openclaw succeeded but no executable path was captured.
  echo See "%OUT%\where_openclaw.txt"
  exit /b 3
)

echo [R42CW] Using OpenClaw command: "%OPENCLAW_CMD%"
call "%OPENCLAW_CMD%" --version > "%OUT%\openclaw_version.txt" 2>&1
if errorlevel 1 (
  echo [FAIL] OpenClaw exists but --version failed. See "%OUT%\openclaw_version.txt".
  exit /b 4
)

set "CAMOFOX_BIND_HOST=127.0.0.1"
if /i "%YTCE_R42CU_CAMOFOX_TELEMETRY%"=="true" (
  set "CAMOFOX_CRASH_REPORT_ENABLED=true"
) else (
  set "CAMOFOX_CRASH_REPORT_ENABLED=false"
)
set "CAMOFOX_INTERACTIVE=%YTCE_R42CU_CAMOFOX_INTERACTIVE%"
if "%CAMOFOX_INTERACTIVE%"=="" set "CAMOFOX_INTERACTIVE=off"
if "%CAMOUFOX_EXECUTABLE%"=="" set "CAMOUFOX_EXECUTABLE=C:\Users\fahad\AppData\Local\camoufox\camoufox\Cache\browsers\official\152.0.4-beta.29-b9ccdc29\camoufox.exe"

call "%OPENCLAW_CMD%" config set gateway.mode local > "%OUT%\openclaw_config_gateway_mode_stdout.txt" 2> "%OUT%\openclaw_config_gateway_mode_stderr.txt"
if errorlevel 1 echo [WARN] Could not set gateway.mode local. Continuing; see "%OUT%\openclaw_config_gateway_mode_stderr.txt".

set "INSTALL_OK=0"
call "%OPENCLAW_CMD%" plugins install -l "%PLUGIN%" --force > "%OUT%\openclaw_install_link_short_stdout.txt" 2> "%OUT%\openclaw_install_link_short_stderr.txt"
if not errorlevel 1 set "INSTALL_OK=1"

if "!INSTALL_OK!"=="0" (
  call "%OPENCLAW_CMD%" plugins install --link "%PLUGIN%" --force > "%OUT%\openclaw_install_link_long_stdout.txt" 2> "%OUT%\openclaw_install_link_long_stderr.txt"
  if not errorlevel 1 set "INSTALL_OK=1"
)

if "!INSTALL_OK!"=="0" (
  call "%OPENCLAW_CMD%" plugins install "%PLUGIN%" --force > "%OUT%\openclaw_install_path_stdout.txt" 2> "%OUT%\openclaw_install_path_stderr.txt"
  if not errorlevel 1 set "INSTALL_OK=1"
)

if "!INSTALL_OK!"=="0" (
  echo [FAIL] OpenClaw local plugin install failed using all attempted forms.
  echo Output folder: "%OUT%"
  echo Check: openclaw_install_link_short_stderr.txt, openclaw_install_link_long_stderr.txt, openclaw_install_path_stderr.txt
  exit /b 5
)

call "%OPENCLAW_CMD%" plugins enable camofox-browser > "%OUT%\openclaw_enable_stdout.txt" 2> "%OUT%\openclaw_enable_stderr.txt"
if errorlevel 1 echo [WARN] Plugin enable command failed or is unsupported. Continuing; see "%OUT%\openclaw_enable_stderr.txt".

call "%OPENCLAW_CMD%" plugins list --json > "%OUT%\openclaw_plugins_list.json" 2> "%OUT%\openclaw_plugins_list.stderr.txt"
call "%OPENCLAW_CMD%" plugins inspect camofox-browser --runtime --json > "%OUT%\openclaw_camofox_inspect_runtime.json" 2> "%OUT%\openclaw_camofox_inspect_runtime.stderr.txt"


echo [DONE] R42CW OpenClaw camofox-browser local plugin handled.
echo [INFO] Output: "%OUT%"
exit /b 0
