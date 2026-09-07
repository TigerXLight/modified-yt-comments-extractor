@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42DH] Starting OpenClaw gateway in this foreground CMD window.
echo [R42DH] Keep this window open while testing live OpenClaw RPC/tools.
echo.
where openclaw
echo.
call openclaw gateway run
exit /b %ERRORLEVEL%
