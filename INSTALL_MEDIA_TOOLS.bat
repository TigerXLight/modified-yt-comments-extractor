@echo off
setlocal EnableExtensions

title YouTube Comment Extractor - Install Media Tools

echo.
echo YouTube Comment Extractor - Optional Media Tools Installer
echo ==========================================================
echo.
echo This helper installs:
echo - VLC Media Player  : transcript timeline playback
echo - FFmpeg            : waveform generation
echo.
echo It uses Windows Package Manager / winget.
echo.
echo If Windows asks for permission, allow the installer.
echo.

where winget >nul 2>&1
if errorlevel 1 (
    echo [MISSING] winget was not found.
    echo.
    echo winget is normally installed through Microsoft App Installer.
    echo Opening Microsoft Store App Installer page...
    echo.
    start "" "ms-windows-store://pdp/?ProductId=9NBLGGH4NNS1"
    echo.
    echo After installing App Installer, run this file again.
    echo.
    pause
    exit /b 1
)

echo [1/2] Installing/updating VLC Media Player...
echo.
winget install -e --id VideoLAN.VLC --accept-source-agreements --accept-package-agreements

echo.
echo [2/2] Installing/updating FFmpeg...
echo.
winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements

echo.
echo Installation commands finished.
echo.
echo Important:
echo - Restart YouTube Comment Extractor after installing VLC.
echo - If FFmpeg was just installed, close and reopen the app.
echo - In some cases, Windows may need a new terminal/session before PATH updates are visible.
echo.

if exist "%~dp0CHECK_MEDIA_TOOLS.bat" (
    call "%~dp0CHECK_MEDIA_TOOLS.bat"
) else (
    pause
)

endlocal
