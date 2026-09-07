@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0..\.." || exit /b 1
set "ROOT=%CD%"
set "BASE=%ROOT%\profile_media_live_captures"
set "OVERLAY=%BASE%\link_source_role_webview_overlay"
set "BACKUPS=%BASE%\r42cl_clean_archive_material_test_backups"
for /f "tokens=1-4 delims=/-. " %%a in ("%date%") do set "D=%%d%%b%%c"
for /f "tokens=1-4 delims=:. " %%a in ("%time%") do set "T=%%a%%b%%c"
set "T=%T: =0%"
set "STAMP=%D%_%T%"
set "BACKUP=%BACKUPS%\r42cl_%STAMP%"
mkdir "%BACKUP%" 2>nul

echo ===== R42CL clean archive material test prep =====
echo ROOT   : %ROOT%
echo BACKUP : %BACKUP%

echo Killing old helper/app processes...
taskkill /F /IM YTCE.NativeSourceRoleEditor.R42CI.exe 2>nul
taskkill /F /IM YTCE.NativeSourceRoleEditor.R42CJ.exe 2>nul
taskkill /F /IM YTCE.NativeSourceRoleEditor.R42CK.exe 2>nul
taskkill /F /IM python.exe 2>nul

if exist "%OVERLAY%" (
  echo Moving overlay/roleplan/cache folder to backup...
  move "%OVERLAY%" "%BACKUP%\link_source_role_webview_overlay" >nul
) else (
  echo Overlay folder did not exist.
)
mkdir "%OVERLAY%" 2>nul

set "UDF=%LOCALAPPDATA%\YTCE\WebView2SourceRoleEditor"
if exist "%UDF%" (
  echo Moving WebView2 user-data folder to backup for clean browser-profile test...
  move "%UDF%" "%BACKUP%\WebView2SourceRoleEditor" >nul
) else (
  echo WebView2 user-data folder did not exist.
)
mkdir "%LOCALAPPDATA%\YTCE" 2>nul

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $root=(Get-Location).Path; $path=Join-Path $root 'profile_media_live_captures\r42cl_clean_archive_material_test_start.json'; $data=[ordered]@{ started_at=(Get-Date).ToString('o'); root=$root; target_archive_url='https://archive.ph/6mr3C'; target_title='People shout ""seagull eater"" at me in the street after far right lies'; backup='%BACKUP%' }; $data | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $path -Encoding UTF8; Write-Host 'START_MARKER:' $path"

echo.
echo Clean prep complete. Now run:
echo   tools\webview2_source_role_editor_native\build_r42ai_native_source_role_editor.cmd
echo   C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe main.py
echo.
echo Then input the 3-link TXT and let the app process it. Do not use the edit window for the test.
echo After the run, use:
echo   tools\webview2_source_role_editor_native\verify_r42cl_archive_material_test.cmd
