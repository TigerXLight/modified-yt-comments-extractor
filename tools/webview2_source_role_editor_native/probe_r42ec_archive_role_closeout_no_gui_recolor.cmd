@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42EC] NO-GUI / NO-NETWORK archive role closeout probe with recolor fixture...
call "%~dp0_r42ec_python.cmd" profile_media_archive_role_closeout_r42ec.py --recolor
exit /b %ERRORLEVEL%
