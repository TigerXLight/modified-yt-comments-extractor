@echo off
setlocal EnableExtensions
cd /d "%~dp0..\.."
set "ROOT=%CD%"
set "OUT=%ROOT%\profile_media_live_captures\r42cy_openclaw_camofox"
echo [R42CY] Output folder: "%OUT%"
if not exist "%OUT%" (
  echo [FAIL] Output folder not found.
  exit /b 2
)
for %%F in (
where_openclaw.txt
openclaw_version.txt
npm_install_ignore_scripts_stderr.txt
openclaw_plugins_validate_stderr.txt
openclaw_install_link_short_accept_stderr.txt
openclaw_install_path_link_accept_stderr.txt
openclaw_install_path_accept_stderr.txt
openclaw_enable_accept_stderr.txt
openclaw_plugins_list.stderr.txt
openclaw_camofox_inspect_cold.stderr.txt
openclaw_camofox_inspect_runtime.stderr.txt
openclaw_gateway_status.stderr.txt
openclaw_config_patch_stdout.json
openclaw_config_patch_stderr.txt
r42cy_inventory_stdout.json
r42cy_inventory_stderr.txt
r42cy_openclaw_inventory_summary.txt
) do (
  if exist "%OUT%\%%F" (
    echo.
    echo ===== %%F =====
    type "%OUT%\%%F"
  )
)
exit /b 0
