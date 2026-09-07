@echo off
setlocal EnableExtensions
cd /d "%~dp0..\.."
set "ROOT=%CD%"
set "OUT=%ROOT%\profile_media_live_captures\r42cx_openclaw_camofox"
echo [R42CX] Output folder: "%OUT%"
if not exist "%OUT%" (
  echo [FAIL] Output folder not found.
  exit /b 2
)
for %%F in (
  where_openclaw.txt
  openclaw_version.txt
  npm_install_ignore_scripts_stderr.txt
  openclaw_plugins_validate_stderr.txt
  openclaw_install_link_short_stderr.txt
  openclaw_install_path_link_stderr.txt
  openclaw_install_path_stderr.txt
  openclaw_config_patch_stdout.json
  openclaw_config_patch_stderr.txt
  openclaw_enable_stderr.txt
  openclaw_plugins_registry_refresh_stderr.txt
  openclaw_plugins_list.stderr.txt
  openclaw_camofox_inspect_cold.stderr.txt
  openclaw_camofox_inspect_runtime.stderr.txt
  openclaw_gateway_status.stderr.txt
  python_inventory_stderr.txt
) do (
  echo.
  echo ===== %%F =====
  if exist "%OUT%\%%F" (
    type "%OUT%\%%F"
  ) else (
    echo [missing]
  )
)
exit /b 0
