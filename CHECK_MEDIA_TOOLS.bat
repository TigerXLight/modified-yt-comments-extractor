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


echo.
echo whisper.cpp Vulkan check:
if exist "C:\whisper.cpp\build-vulkan\bin\Release\whisper-cli.exe" (
    echo [OK] whisper.cpp CLI found.
) else (
    echo [MISSING] whisper.cpp CLI was not found at C:\whisper.cpp\build-vulkan\bin\Release\whisper-cli.exe
)

if exist "C:\whisper.cpp\ggml-large-v3.bin" (
    echo [OK] whisper.cpp large-v3 model found.
) else if exist "C:\whisper.cpp\models\ggml-large-v3.bin" (
    echo [OK] whisper.cpp large-v3 model found in models folder.
) else (
    echo [MISSING] whisper.cpp large-v3 model was not found.
)

if exist "C:\whisper.cpp\ggml-large-v3-turbo.bin" (
    echo [OK] whisper.cpp large-v3-turbo model found.
) else if exist "C:\whisper.cpp\models\ggml-large-v3-turbo.bin" (
    echo [OK] whisper.cpp large-v3-turbo model found in models folder.
) else (
    echo [INFO] whisper.cpp large-v3-turbo model was not found. Turbo candidate will be skipped.
)

echo If something was just installed, close and reopen the app before testing again.
echo.
pause

endlocal
