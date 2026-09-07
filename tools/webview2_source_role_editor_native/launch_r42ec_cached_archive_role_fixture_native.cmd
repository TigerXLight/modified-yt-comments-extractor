@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42EC] Optional local-fixture native WebView2 visual check.
echo [R42EC] This opens only the native helper on a file:/// fixture. It does NOT open archive.ph or the full app.
call "%~dp0_r42ec_python.cmd" profile_media_archive_role_local_fixture_r42eb.py --launch-native-local-fixture
exit /b %ERRORLEVEL%
