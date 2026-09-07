@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0..\.."
set "ROOT=%CD%"
set "PLUGIN=%ROOT%\tools\camofox_browser_backend_r42cu\jo_inc_camofox_browser"
set "OUT=%ROOT%\profile_media_live_captures\r42cx_openclaw_camofox"
mkdir "%OUT%" 2>nul

echo [R42CX] Root: "%ROOT%"
echo [R42CX] Plugin path: "%PLUGIN%"

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
  echo [INFO] Output: "%OUT%"
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

echo [R42CX] Using OpenClaw command: "%OPENCLAW_CMD%"
call "%OPENCLAW_CMD%" --version > "%OUT%\openclaw_version.txt" 2>&1
if errorlevel 1 (
  echo [FAIL] OpenClaw exists but --version failed. See "%OUT%\openclaw_version.txt".
  exit /b 4
)
type "%OUT%\openclaw_version.txt"

rem Local defaults for the YTCE-managed camofox-browser backend.
set "CAMOFOX_BIND_HOST=127.0.0.1"
set "CAMOFOX_CRASH_REPORT_ENABLED=false"
set "CAMOFOX_INTERACTIVE=%YTCE_R42CU_CAMOFOX_INTERACTIVE%"
if "%CAMOFOX_INTERACTIVE%"=="" set "CAMOFOX_INTERACTIVE=off"
if "%CAMOUFOX_EXECUTABLE%"=="" set "CAMOUFOX_EXECUTABLE=C:\Users\fahad\AppData\Local\camoufox\camoufox\Cache\browsers\official\152.0.4-beta.29-b9ccdc29\camoufox.exe"

rem Avoid OpenClaw's model/memory warning during this plugin-only integration unless the user wants it.
if /i "%YTCE_R42CX_DISABLE_OPENCLAW_MEMORY_SEARCH%"=="1" (
  call "%OPENCLAW_CMD%" config set memory.search.enabled false > "%OUT%\openclaw_config_memory_search_stdout.txt" 2> "%OUT%\openclaw_config_memory_search_stderr.txt"
)

call "%OPENCLAW_CMD%" config set gateway.mode local > "%OUT%\openclaw_config_gateway_mode_stdout.txt" 2> "%OUT%\openclaw_config_gateway_mode_stderr.txt"
if errorlevel 1 echo [WARN] Could not set gateway.mode local. Continuing; see "%OUT%\openclaw_config_gateway_mode_stderr.txt".

rem Install runtime deps for the bundled jo-inc server without downloading a Camoufox browser binary.
rem The real Camoufox executable is already available and provided by CAMOUFOX_EXECUTABLE.
if exist "%PLUGIN%\package.json" (
  echo [R42CX] Ensuring jo-inc/camofox-browser npm dependencies using --ignore-scripts...
  pushd "%PLUGIN%" >nul
  call npm install --omit=dev --ignore-scripts > "%OUT%\npm_install_ignore_scripts_stdout.txt" 2> "%OUT%\npm_install_ignore_scripts_stderr.txt"
  if errorlevel 1 (
    echo [WARN] npm install failed. OpenClaw plugin install may still work if dependencies already exist.
    echo [WARN] See "%OUT%\npm_install_ignore_scripts_stderr.txt"
  ) else (
    echo [PASS] npm dependencies present for bundled camofox-browser server.
  )
  popd >nul
)

call "%OPENCLAW_CMD%" plugins validate --root "%PLUGIN%" --json > "%OUT%\openclaw_plugins_validate_stdout.json" 2> "%OUT%\openclaw_plugins_validate_stderr.txt"
if errorlevel 1 echo [WARN] OpenClaw plugin validate reported an issue; install/config fallback will still run.

set "INSTALL_OK=0"
set "INSTALL_FORM=none"
call "%OPENCLAW_CMD%" plugins install -l "%PLUGIN%" --force > "%OUT%\openclaw_install_link_short_stdout.txt" 2> "%OUT%\openclaw_install_link_short_stderr.txt"
if not errorlevel 1 (
  set "INSTALL_OK=1"
  set "INSTALL_FORM=plugins install -l"
)

if "!INSTALL_OK!"=="0" (
  call "%OPENCLAW_CMD%" plugins install "%PLUGIN%" --link --force > "%OUT%\openclaw_install_path_link_stdout.txt" 2> "%OUT%\openclaw_install_path_link_stderr.txt"
  if not errorlevel 1 (
    set "INSTALL_OK=1"
    set "INSTALL_FORM=plugins install path --link"
  )
)

if "!INSTALL_OK!"=="0" (
  call "%OPENCLAW_CMD%" plugins install "%PLUGIN%" --force > "%OUT%\openclaw_install_path_stdout.txt" 2> "%OUT%\openclaw_install_path_stderr.txt"
  if not errorlevel 1 (
    set "INSTALL_OK=1"
    set "INSTALL_FORM=plugins install path"
  )
)

if "!INSTALL_OK!"=="0" (
  echo [WARN] OpenClaw managed local plugin install failed using all attempted forms.
  echo [WARN] Applying documented plugins.load.paths fallback into ~/.openclaw/openclaw.json ...
  "C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe" "%ROOT%\profile_media_openclaw_config_patch_r42cx.py" --plugin-path "%PLUGIN%" > "%OUT%\openclaw_config_patch_stdout.json" 2> "%OUT%\openclaw_config_patch_stderr.txt"
  if errorlevel 1 (
    echo [FAIL] OpenClaw config fallback failed. See "%OUT%\openclaw_config_patch_stderr.txt".
    call :dump_errors
    exit /b 5
  )
  set "INSTALL_FORM=plugins.load.paths fallback"
) else (
  echo [PASS] OpenClaw plugin install succeeded using: !INSTALL_FORM!
)

call "%OPENCLAW_CMD%" plugins enable camofox-browser > "%OUT%\openclaw_enable_stdout.txt" 2> "%OUT%\openclaw_enable_stderr.txt"
if errorlevel 1 echo [WARN] Plugin enable command failed or is unsupported. Continuing; see "%OUT%\openclaw_enable_stderr.txt".

call "%OPENCLAW_CMD%" plugins registry --refresh > "%OUT%\openclaw_plugins_registry_refresh_stdout.txt" 2> "%OUT%\openclaw_plugins_registry_refresh_stderr.txt"
if errorlevel 1 echo [WARN] Registry refresh failed. Continuing; see "%OUT%\openclaw_plugins_registry_refresh_stderr.txt".

call "%OPENCLAW_CMD%" plugins list --json > "%OUT%\openclaw_plugins_list.json" 2> "%OUT%\openclaw_plugins_list.stderr.txt"
call "%OPENCLAW_CMD%" plugins inspect camofox-browser --json > "%OUT%\openclaw_camofox_inspect_cold.json" 2> "%OUT%\openclaw_camofox_inspect_cold.stderr.txt"
call "%OPENCLAW_CMD%" plugins inspect camofox-browser --runtime --json > "%OUT%\openclaw_camofox_inspect_runtime.json" 2> "%OUT%\openclaw_camofox_inspect_runtime.stderr.txt"

if exist "%OUT%\openclaw_camofox_inspect_runtime.json" (
  echo [INFO] Runtime inspect output: "%OUT%\openclaw_camofox_inspect_runtime.json"
)

echo [DONE] R42CX OpenClaw camofox-browser handled by: !INSTALL_FORM!
echo [INFO] Output: "%OUT%"
exit /b 0

:dump_errors
echo --- openclaw_install_link_short_stderr.txt ---
if exist "%OUT%\openclaw_install_link_short_stderr.txt" type "%OUT%\openclaw_install_link_short_stderr.txt"
echo --- openclaw_install_path_link_stderr.txt ---
if exist "%OUT%\openclaw_install_path_link_stderr.txt" type "%OUT%\openclaw_install_path_link_stderr.txt"
echo --- openclaw_install_path_stderr.txt ---
if exist "%OUT%\openclaw_install_path_stderr.txt" type "%OUT%\openclaw_install_path_stderr.txt"
exit /b 0
