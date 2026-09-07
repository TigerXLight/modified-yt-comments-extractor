@echo off
setlocal
pushd "%~dp0..\.." || exit /b 1
call "%~dp0_r42dg_python.cmd" "%CD%\profile_media_openclaw_remaining_marketplace_retry_r42dg.py" retry-remaining %*
set "RC=%ERRORLEVEL%"
popd
exit /b %RC%
