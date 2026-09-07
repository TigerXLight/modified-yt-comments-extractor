@echo off
setlocal EnableExtensions
cd /d "%~dp0..\.."
set "ROOT=%CD%"
for /f "tokens=1-4 delims=/.: " %%a in ("%DATE% %TIME%") do set STAMP=%%d%%b%%c_%%a
set "OUT=%USERPROFILE%\Downloads\ytce_r42cv_openclaw_camofox_debug_%STAMP%.zip"
set "TMP=%TEMP%\ytce_r42cv_debug_%RANDOM%%RANDOM%"
mkdir "%TMP%" 2>nul
if exist "profile_media_live_captures\r42cv_openclaw_camofox" xcopy /e /i /y "profile_media_live_captures\r42cv_openclaw_camofox" "%TMP%\r42cv_openclaw_camofox" >nul
if exist "profile_media_live_captures\r42ct_archive_source_material" xcopy /e /i /y "profile_media_live_captures\r42ct_archive_source_material" "%TMP%\r42ct_archive_source_material" >nul
if exist "profile_media_live_captures\r42cu_camofox_browser_backend" xcopy /e /i /y "profile_media_live_captures\r42cu_camofox_browser_backend" "%TMP%\r42cu_camofox_browser_backend" >nul
copy /y "R42CV_IMPLEMENTATION_CHECKLIST_20260906.md" "%TMP%\" >nul 2>nul
copy /y "CAMOUFOX_FEATURE_PARITY_BACKUP_R42CV.md" "%TMP%\" >nul 2>nul
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -LiteralPath '%TMP%\*' -DestinationPath '%OUT%' -Force"
echo Created R42CV debug ZIP: "%OUT%"
exit /b 0
