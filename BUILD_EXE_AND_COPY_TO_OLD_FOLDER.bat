@echo off
cd /d "%~dp0"

call BUILD_EXE.bat
call COPY_TO_OLD_FOLDER.bat