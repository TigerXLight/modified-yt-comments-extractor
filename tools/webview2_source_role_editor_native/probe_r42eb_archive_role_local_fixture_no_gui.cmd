@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42EB] NO-GUI / NO-NETWORK / NO-ARCHIVE-HIT cached archive local-fixture audit...
call "%~dp0_r42eb_python.cmd" profile_media_archive_role_local_fixture_r42eb.py "https://archive.ph/6mr3C"
exit /b %ERRORLEVEL%
