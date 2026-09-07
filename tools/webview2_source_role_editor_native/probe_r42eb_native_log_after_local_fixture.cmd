@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42EB] Probing native helper log after optional local-fixture visual check...
call "%~dp0_r42eb_python.cmd" profile_media_archive_role_local_fixture_r42eb.py --probe-native-log
exit /b %ERRORLEVEL%
