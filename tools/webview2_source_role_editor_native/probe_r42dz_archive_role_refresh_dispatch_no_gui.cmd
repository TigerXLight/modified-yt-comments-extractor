@echo off
setlocal
echo [R42DZ] NO-GUI / NO-NETWORK archive role-refresh dispatch dry run...
call "%~dp0_r42dz_python.cmd" profile_media_archive_role_refresh_dispatch_r42dz.py https://archive.ph/6mr3C || exit /b 1
endlocal
