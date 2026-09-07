@echo off
setlocal
echo [R42DE] Starting OpenClaw gateway in foreground. Leave this window open while testing.
call openclaw gateway run
exit /b %ERRORLEVEL%
