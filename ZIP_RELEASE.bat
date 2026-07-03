@echo off
cd /d "%~dp0"

set VERSION=2.3.0
set ZIP_NAME=YouTube-Comment-Extractor-Windows-v%VERSION%.zip

echo Closing running app if open...
taskkill /f /im "YouTube Comment Extractor.exe" >nul 2>&1

if not exist "dist\YouTube Comment Extractor" (
    echo ERROR: dist\YouTube Comment Extractor does not exist.
    echo Run BUILD_EXE.bat first.
    pause
    exit /b
)

echo Creating release ZIP: %ZIP_NAME%
powershell -NoProfile -Command "Compress-Archive -LiteralPath '.\dist\YouTube Comment Extractor' -DestinationPath '.\%ZIP_NAME%' -Force"

echo.
echo ZIP created:
echo %cd%\%ZIP_NAME%
pause