@echo off
setlocal EnableExtensions
cd /d "%~dp0..\.."
set "ROOT=%CD%"
set "STAMP=%DATE:~-4%%DATE:~3,2%%DATE:~0,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
set "STAMP=%STAMP: =0%"
set "OUTDIR=%ROOT%\profile_media_live_captures\r42cy_openclaw_camofox"
set "ZIP=%ROOT%\profile_media_live_captures\r42cy_openclaw_camofox_debug_%STAMP%.zip"
set "DLZIP=%USERPROFILE%\Downloads\r42cy_openclaw_camofox_debug_%STAMP%.zip"
if not exist "%OUTDIR%" (
  echo [FAIL] Output folder not found: "%OUTDIR%"
  exit /b 2
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $out='%OUTDIR%'; $zip='%ZIP%'; $dl='%DLZIP%'; if(Test-Path -LiteralPath $zip){Remove-Item -LiteralPath $zip -Force}; Compress-Archive -LiteralPath (Join-Path $out '*') -DestinationPath $zip -Force; Copy-Item -LiteralPath $zip -Destination $dl -Force; Write-Host '[DONE] Created project ZIP:' $zip; Write-Host '[DONE] Copied to Downloads:' $dl; Write-Host '[INFO] Select project ZIP with:'; Write-Host ('explorer.exe /select,"' + $zip + '"')"
exit /b 0
