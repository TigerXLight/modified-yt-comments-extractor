@echo off
set SOURCE=T:\References\to go\Media\tools\Modified YouTube comment extractor
set DEST=T:\References\to go\Media\tools\yt-comments-extractor

echo Closing running app if open...
taskkill /f /im "YouTube Comment Extractor.exe" >nul 2>&1

echo Copying source files...
robocopy "%SOURCE%" "%DEST%" main.py extractor.py spam_filter.py transcript_tools.py requirements.txt README.md RELEASE_NOTES.md LICENSE run_app.bat updater.py evidence_exporter.py /R:1 /W:1
echo Copying core folder...
robocopy "%SOURCE%\core" "%DEST%\core" /E /R:1 /W:1

echo Copying assets folder...
robocopy "%SOURCE%\assets" "%DEST%\assets" /E /R:1 /W:1

echo Replacing old EXE/dist folder...
rmdir /s /q "%DEST%\dist\YouTube Comment Extractor" 2>nul

robocopy "%SOURCE%\dist\YouTube Comment Extractor" "%DEST%\dist\YouTube Comment Extractor" /E /R:1 /W:1

echo.
echo Done. Old folder has been updated.
pause