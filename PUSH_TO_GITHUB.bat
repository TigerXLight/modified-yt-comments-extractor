@echo off
cd /d "%~dp0"

echo Current Git status:
git status

echo.
set /p MSG=Enter commit message: 

if "%MSG%"=="" (
    echo No commit message entered. Cancelling.
    pause
    exit /b
)

git add main.py extractor.py updater.py evidence_exporter.py asr_defaults.py asr_tools.py transcript_tools.py youtube_transcript_downloader.py youtube_video_metadata.py README.md RELEASE_NOTES.md requirements.txt core assets *.bat .gitignore
git commit -m "%MSG%"
git push

echo.
echo Done.
pause