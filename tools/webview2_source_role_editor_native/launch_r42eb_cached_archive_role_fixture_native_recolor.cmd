@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42EB] Optional local-fixture native WebView2 visual check with recolor payload.
echo [R42EB] This opens only the native helper on a file:/// fixture. It does NOT open archive.ph or the full app.
call "%~dp0_r42eb_python.cmd" profile_media_archive_role_local_fixture_r42eb.py "https://archive.ph/6mr3C" --launch-native-local-fixture --recolor
exit /b %ERRORLEVEL%
