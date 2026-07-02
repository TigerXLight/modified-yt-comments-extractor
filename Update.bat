@echo off
cd /d "%~dp0"

echo Checking local Git status...
git status --porcelain > "%TEMP%\yt_status.txt"

for %%A in ("%TEMP%\yt_status.txt") do if %%~zA neq 0 (
    echo.
    echo You have local changes.
    echo Commit, stash, or discard them before updating.
    echo.
    git status
    pause
    exit /b
)

echo Pulling latest source from GitHub...
git pull --rebase origin main

if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo Updating requirements...
python -m pip install --upgrade pip
pip install keyring
pip install -r requirements.txt

echo Done.
pause