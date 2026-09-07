@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0..\.."
set "ROOT=%CD%"
set "PLUGIN=%ROOT%\tools\camofox_browser_backend_r42cu\jo_inc_camofox_browser"
set "OUT=%ROOT%\profile_media_live_captures\r42cy_openclaw_camofox"
mkdir "%OUT%" 2>nul

echo [R42CY] Root: "%ROOT%"
echo [R42CY] Plugin path: "%PLUGIN%"

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
if not defined OPENCLAW_CMD (
  echo [FAIL] where openclaw succeeded but no .cmd/executable was captured.
  echo [INFO] See "%OUT%\where_openclaw.txt"
  exit /b 3
)
if not exist "%PLUGIN%\openclaw.plugin.json" (
  echo [FAIL] Bundled camofox-browser OpenClaw plugin manifest not found:
  echo        "%PLUGIN%\openclaw.plugin.json"
  exit /b 4
)

echo [R42CY] Using OpenClaw command: "%OPENCLAW_CMD%"
call "%OPENCLAW_CMD%" --version > "%OUT%\openclaw_version.txt" 2>&1
if errorlevel 1 (
  echo [FAIL] OpenClaw exists but --version failed. See "%OUT%\openclaw_version.txt".
  exit /b 5
)
type "%OUT%\openclaw_version.txt"

rem YTCE-local defaults for the camofox-browser backend. These affect the bundled server
rem when it is started by YTCE or OpenClaw plugin config, without broadening OpenClaw itself.
set "CAMOFOX_BIND_HOST=127.0.0.1"
set "CAMOFOX_CRASH_REPORT_ENABLED=false"
set "CAMOFOX_INTERACTIVE=%YTCE_R42CU_CAMOFOX_INTERACTIVE%"
if "%CAMOFOX_INTERACTIVE%"=="" set "CAMOFOX_INTERACTIVE=off"
if "%CAMOUFOX_EXECUTABLE%"=="" set "CAMOUFOX_EXECUTABLE=C:\Users\fahad\AppData\Local\camoufox\camoufox\Cache\browsers\official\152.0.4-beta.29-b9ccdc29\camoufox.exe"

rem Do NOT set gateway.mode here. OpenClaw 2026.9.x may reject gateway.mode as removed,
rem even though doctor may print older text. R42CY only handles plugin registration.

rem Install jo-inc/camofox-browser dependencies locally. Use --ignore-scripts so npm does
rem not download another Camoufox browser; the existing external Camoufox executable is used.
if exist "%PLUGIN%\package.json" (
  echo [R42CY] Ensuring jo-inc/camofox-browser npm dependencies using --omit=dev --ignore-scripts...
  pushd "%PLUGIN%" >nul
  call npm install --omit=dev --ignore-scripts > "%OUT%\npm_install_ignore_scripts_stdout.txt" 2> "%OUT%\npm_install_ignore_scripts_stderr.txt"
  if errorlevel 1 (
    echo [WARN] npm install failed. See "%OUT%\npm_install_ignore_scripts_stderr.txt"
  ) else (
    echo [PASS] npm dependencies present for bundled camofox-browser server.
  )
  popd >nul
)

rem Validate if this OpenClaw CLI supports validation. Known issue: some versions throw
rem Cannot read properties of undefined (reading 'pluginConfig'), so failure is logged only.
call "%OPENCLAW_CMD%" plugins validate --root "%PLUGIN%" --json > "%OUT%\openclaw_plugins_validate_stdout.json" 2> "%OUT%\openclaw_plugins_validate_stderr.txt"
if errorlevel 1 echo [WARN] OpenClaw plugin validate reported an issue; continuing to explicit install with capability acceptance.

set "INSTALL_OK=0"
set "INSTALL_FORM=none"

rem OpenClaw now requires explicit capability consent for this plugin. The important change
rem from R42CX is --accept-capabilities. A bare plugins.load.paths fallback cannot persist
rem capability acceptance, so managed linked install is preferred.
call "%OPENCLAW_CMD%" plugins install -l "%PLUGIN%" --force --accept-capabilities > "%OUT%\openclaw_install_link_short_accept_stdout.txt" 2> "%OUT%\openclaw_install_link_short_accept_stderr.txt"
if not errorlevel 1 (
  set "INSTALL_OK=1"
  set "INSTALL_FORM=plugins install -l --force --accept-capabilities"
)

if "!INSTALL_OK!"=="0" (
  call "%OPENCLAW_CMD%" plugins install "%PLUGIN%" --link --force --accept-capabilities > "%OUT%\openclaw_install_path_link_accept_stdout.txt" 2> "%OUT%\openclaw_install_path_link_accept_stderr.txt"
  if not errorlevel 1 (
    set "INSTALL_OK=1"
    set "INSTALL_FORM=plugins install path --link --force --accept-capabilities"
  )
)

if "!INSTALL_OK!"=="0" (
  call "%OPENCLAW_CMD%" plugins install "%PLUGIN%" --force --accept-capabilities > "%OUT%\openclaw_install_path_accept_stdout.txt" 2> "%OUT%\openclaw_install_path_accept_stderr.txt"
  if not errorlevel 1 (
    set "INSTALL_OK=1"
    set "INSTALL_FORM=plugins install path --force --accept-capabilities"
  )
)

if "!INSTALL_OK!"=="0" (
  echo [WARN] Managed local plugin install still failed.
  echo [WARN] Applying cold-inspection fallback WITHOUT pretending capability acceptance was persisted.
  "C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe" "%ROOT%\profile_media_openclaw_config_patch_r42cy.py" --plugin-path "%PLUGIN%" > "%OUT%\openclaw_config_patch_stdout.json" 2> "%OUT%\openclaw_config_patch_stderr.txt"
  if errorlevel 1 (
    echo [FAIL] OpenClaw config fallback failed. See "%OUT%\openclaw_config_patch_stderr.txt".
    call :dump_errors
    exit /b 6
  )
  set "INSTALL_FORM=plugins.load.paths cold-inspection fallback"
) else (
  echo [PASS] OpenClaw managed linked install succeeded using: !INSTALL_FORM!
)

call "%OPENCLAW_CMD%" plugins enable camofox-browser --accept-capabilities > "%OUT%\openclaw_enable_accept_stdout.txt" 2> "%OUT%\openclaw_enable_accept_stderr.txt"
if errorlevel 1 echo [WARN] Plugin enable with capability acceptance failed or is unsupported. See "%OUT%\openclaw_enable_accept_stderr.txt".

call "%OPENCLAW_CMD%" plugins list --json > "%OUT%\openclaw_plugins_list.json" 2> "%OUT%\openclaw_plugins_list.stderr.txt"
call "%OPENCLAW_CMD%" plugins inspect camofox-browser --json > "%OUT%\openclaw_camofox_inspect_cold.json" 2> "%OUT%\openclaw_camofox_inspect_cold.stderr.txt"
call "%OPENCLAW_CMD%" plugins inspect camofox-browser --runtime --json > "%OUT%\openclaw_camofox_inspect_runtime.json" 2> "%OUT%\openclaw_camofox_inspect_runtime.stderr.txt"
call "%OPENCLAW_CMD%" gateway status --json > "%OUT%\openclaw_gateway_status.json" 2> "%OUT%\openclaw_gateway_status.stderr.txt"

"C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe" "%ROOT%\profile_media_openclaw_plugin_inventory_r42cy.py" --output-dir "%OUT%" > "%OUT%\r42cy_inventory_stdout.json" 2> "%OUT%\r42cy_inventory_stderr.txt"

echo [DONE] R42CY OpenClaw camofox-browser handled by: !INSTALL_FORM!
echo [INFO] Output: "%OUT%"
echo [INFO] Next: tools\webview2_source_role_editor_native\probe_r42cy_openclaw_camofox_plugin.cmd
exit /b 0

:dump_errors
echo --- openclaw_install_link_short_accept_stderr.txt ---
if exist "%OUT%\openclaw_install_link_short_accept_stderr.txt" type "%OUT%\openclaw_install_link_short_accept_stderr.txt"
echo --- openclaw_install_path_link_accept_stderr.txt ---
if exist "%OUT%\openclaw_install_path_link_accept_stderr.txt" type "%OUT%\openclaw_install_path_link_accept_stderr.txt"
echo --- openclaw_install_path_accept_stderr.txt ---
if exist "%OUT%\openclaw_install_path_accept_stderr.txt" type "%OUT%\openclaw_install_path_accept_stderr.txt"
exit /b 0
