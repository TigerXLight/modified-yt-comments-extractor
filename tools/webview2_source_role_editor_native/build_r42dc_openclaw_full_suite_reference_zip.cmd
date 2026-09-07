@echo off
setlocal
cd /d "%~dp0\..\.."
if not exist "tools\openclaw_reference_layer_r42dc" (
  echo [FAIL] Could not locate project root from script path.
  exit /b 1
)
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set STAMP=%%i
set OUTDIR=profile_media_live_captures\r42dc_openclaw_full_suite_reference
set ZIP=%OUTDIR%\r42dc_openclaw_full_suite_reference_%STAMP%.zip
mkdir "%OUTDIR%" 2>nul
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $root=(Get-Location).Path; $tmp=Join-Path $env:TEMP ('r42dc_ref_' + [guid]::NewGuid().ToString('N')); New-Item -ItemType Directory -Force -Path $tmp | Out-Null; Copy-Item -LiteralPath (Join-Path $root 'R42DB_OPENCLAW_ALL_PLUGIN_IMPLEMENTATION_MAP_20260906.md') -Destination $tmp -Force -ErrorAction SilentlyContinue; Copy-Item -LiteralPath (Join-Path $root 'R42DC_OPENCLAW_FULL_SUITE_INTAKE_NOTES_20260906.md') -Destination $tmp -Force -ErrorAction SilentlyContinue; Copy-Item -LiteralPath (Join-Path $root 'openclaw_all_plugin_marketplace_manifest_r42dc.json') -Destination $tmp -Force -ErrorAction SilentlyContinue; Copy-Item -LiteralPath (Join-Path $root 'tools\openclaw_reference_layer_r42dc') -Destination (Join-Path $tmp 'openclaw_reference_layer_r42dc') -Recurse -Force; Compress-Archive -LiteralPath (Join-Path $tmp '*') -DestinationPath '%ZIP%' -Force; Copy-Item -LiteralPath '%ZIP%' -Destination (Join-Path $env:USERPROFILE 'Downloads') -Force; Write-Host '[DONE] Created:' (Resolve-Path '%ZIP%'); Write-Host '[DONE] Copied to Downloads.'"
endlocal
