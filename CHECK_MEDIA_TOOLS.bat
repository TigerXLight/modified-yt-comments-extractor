@echo off
setlocal EnableExtensions

title YouTube Comment Extractor - Check Media Tools

echo.
echo YouTube Comment Extractor - Media Tools Check
echo =============================================
echo.

set "VLC_FOUND=0"

if exist "%ProgramFiles%\VideoLAN\VLC\libvlc.dll" (
    set "VLC_FOUND=1"
    set "VLC_LOCATION=%ProgramFiles%\VideoLAN\VLC"
)

if "%VLC_FOUND%"=="0" if exist "%ProgramFiles%\VideoLAN\VLC\vlc.exe" (
    set "VLC_FOUND=1"
    set "VLC_LOCATION=%ProgramFiles%\VideoLAN\VLC"
)

if "%VLC_FOUND%"=="0" (
    where vlc >nul 2>&1
    if not errorlevel 1 (
        set "VLC_FOUND=1"
        set "VLC_LOCATION=Available on PATH"
    )
)

if "%VLC_FOUND%"=="1" (
    echo [OK] VLC/libVLC found: %VLC_LOCATION%
) else (
    echo [MISSING] VLC/libVLC was not found.
    echo          Install VLC Media Player for transcript timeline playback.
)

echo.

where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo [MISSING] FFmpeg was not found on PATH.
    echo          Install FFmpeg for waveform generation.
) else (
    echo [OK] FFmpeg found on PATH.
    for /f "tokens=*" %%A in ('where ffmpeg 2^>nul') do echo      %%A
)

echo.
echo If something was just installed, close and reopen the app before testing again.
echo.
pause

endlocal
