@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42EC] Probing native helper log after local fixture check...
call "%~dp0_r42ec_python.cmd" profile_media_archive_role_local_fixture_r42eb.py --probe-native-log
exit /b %ERRORLEVEL%
