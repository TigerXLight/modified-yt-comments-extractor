@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42DH] OpenClaw gateway status:
call openclaw gateway status --json
exit /b %ERRORLEVEL%
