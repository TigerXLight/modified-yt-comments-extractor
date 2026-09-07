@echo off
setlocal EnableExtensions
cd /d "%~dp0..\.."
set "ROOT=%CD%"
set "BASE=%ROOT%\profile_media_live_captures\r42cz_openclaw_reference_layer"
if not exist "%BASE%" (
  echo [FAIL] Reference layer folder not found: "%BASE%"
  echo Run: tools\webview2_source_role_editor_native\build_r42cz_openclaw_backup_reference_layer.cmd
  exit /b 2
)
for /f "delims=" %%D in ('dir /b /ad /o-d "%BASE%" 2^>nul') do if not defined LAST set "LAST=%%D"
if not defined LAST (
  echo [FAIL] No dated reference layer output folder found under "%BASE%"
  exit /b 3
)
set "STAMP=%DATE:~-4%%DATE:~3,2%%DATE:~0,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
set "STAMP=%STAMP: =0%"
set "ZIP=%ROOT%\profile_media_live_captures\r42cz_openclaw_reference_debug_%STAMP%.zip"
set "DLZIP=%USERPROFILE%\Downloads\r42cz_openclaw_reference_debug_%STAMP%.zip"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $src='%BASE%\%LAST%'; $zip='%ZIP%'; $dl='%DLZIP%'; if(Test-Path -LiteralPath $zip){Remove-Item -LiteralPath $zip -Force}; Compress-Archive -LiteralPath (Join-Path $src '*') -DestinationPath $zip -Force; Copy-Item -LiteralPath $zip -Destination $dl -Force; Write-Host '[DONE] Created project ZIP:' $zip; Write-Host '[DONE] Copied to Downloads:' $dl; Write-Host ('[INFO] Select with: explorer.exe /select,"' + $dl + '"')"
exit /b 0
