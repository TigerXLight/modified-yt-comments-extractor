@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0..\.." || exit /b 1
set "ROOT=%CD%"
set "BASE=%ROOT%\profile_media_live_captures"
set "OVERLAY=%BASE%\link_source_role_webview_overlay"
set "BACKUPS=%BASE%\r42cm_hard_clean_archive_material_test_backups"
for /f "tokens=1-4 delims=/-. " %%a in ("%date%") do set "D=%%d%%b%%c"
for /f "tokens=1-4 delims=:. " %%a in ("%time%") do set "T=%%a%%b%%c"
set "T=%T: =0%"
set "STAMP=%D%_%T%"
set "BACKUP=%BACKUPS%\r42cm_%STAMP%"
mkdir "%BACKUP%" 2>nul

echo ===== R42CM HARD CLEAN archive material test prep =====
echo ROOT   : %ROOT%
echo BACKUP : %BACKUP%

echo Killing old helper/app/WebView2 processes...
taskkill /F /IM YTCE.NativeSourceRoleEditor.R42CI.exe 2>nul
taskkill /F /IM YTCE.NativeSourceRoleEditor.R42CJ.exe 2>nul
taskkill /F /IM YTCE.NativeSourceRoleEditor.R42CK.exe 2>nul
taskkill /F /IM python.exe 2>nul
taskkill /F /IM msedgewebview2.exe 2>nul
ping -n 3 127.0.0.1 >nul

if exist "%OVERLAY%" (
  echo Moving overlay/roleplan/cache folder to backup...
  move "%OVERLAY%" "%BACKUP%\link_source_role_webview_overlay" >nul
  if errorlevel 1 (
    echo FAIL: could not move overlay folder. Close the app/helper/browser and rerun.
    exit /b 2
  )
) else (
  echo Overlay folder did not exist.
)
mkdir "%OVERLAY%" 2>nul

set "UDF=%LOCALAPPDATA%\YTCE\WebView2SourceRoleEditor"
if exist "%UDF%" (
  echo Moving WebView2 user-data folder to backup for clean browser-profile test...
  move "%UDF%" "%BACKUP%\WebView2SourceRoleEditor" >nul
  if errorlevel 1 (
    echo FAIL: could not move WebView2 user-data folder. This test would be contaminated.
    echo Try: taskkill /F /IM msedgewebview2.exe 2^>nul
    echo Then rerun this prepare script. If it still fails, reboot Windows and run prepare before launching the app.
    exit /b 3
  )
) else (
  echo WebView2 user-data folder did not exist.
)
mkdir "%LOCALAPPDATA%\YTCE" 2>nul

echo Moving old test-article live capture folders to backup when found...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0r42cm_move_old_test_article_captures.ps1" -Root "%ROOT%" -Backup "%BACKUP%"
if errorlevel 1 (
  echo FAIL: old test-article capture cleanup failed.
  exit /b 4
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $root=(Get-Location).Path; $path=Join-Path $root 'profile_media_live_captures\r42cm_hard_clean_archive_material_test_start.json'; $data=[ordered]@{ started_at=(Get-Date).ToString('o'); root=$root; target_archive_url='https://archive.ph/6mr3C'; target_title='People shout ""seagull eater"" at me in the street after far right lies'; backup='%BACKUP%'; clean_profile_moved=$true; old_test_captures_moved=$true }; $data | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $path -Encoding UTF8; Write-Host 'START_MARKER:' $path"
if errorlevel 1 exit /b 5

echo.
echo HARD CLEAN prep complete. Now run:
echo   tools\webview2_source_role_editor_native\build_r42ai_native_source_role_editor.cmd
echo   C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe main.py
echo.
echo Then input the 3-link TXT and let the app process it. Do not use old saved review state as proof.
echo After the run, use:
echo   tools\webview2_source_role_editor_native\verify_r42cm_archive_material_test.cmd
