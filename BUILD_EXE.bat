@echo off
cd /d "%~dp0"

echo Closing running app if open...
taskkill /f /im "YouTube Comment Extractor.exe" >nul 2>&1

echo Activating virtual environment...
if not exist "venv\Scripts\python.exe" (
    echo Creating venv...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo Installing/updating build tools...
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller keyring

echo Building EXE...
python -m PyInstaller --noconfirm --clean --windowed --name "YouTube Comment Extractor" --collect-all customtkinter --collect-all faster_whisper --add-data "assets;assets" main.py


echo Copying helper scripts...
if exist "INSTALL_MEDIA_TOOLS.bat" copy /Y "INSTALL_MEDIA_TOOLS.bat" "dist\YouTube Comment Extractor\INSTALL_MEDIA_TOOLS.bat" >nul
if exist "CHECK_MEDIA_TOOLS.bat" copy /Y "CHECK_MEDIA_TOOLS.bat" "dist\YouTube Comment Extractor\CHECK_MEDIA_TOOLS.bat" >nul

echo.
echo Build complete.
echo Output:
echo %cd%\dist\YouTube Comment Extractor
echo.
echo Notes:
echo - Timeline playback requires VLC Media Player installed on the target PC.
echo - Waveform generation requires ffmpeg available on PATH.
echo - python-vlc is installed from requirements.txt, but desktop VLC/libVLC is external.
pause