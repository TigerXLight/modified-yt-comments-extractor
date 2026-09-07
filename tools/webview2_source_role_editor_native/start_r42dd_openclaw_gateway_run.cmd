@echo off
setlocal
echo [R42DD] Starting OpenClaw gateway in this terminal. Leave this window open while testing gateway-backed plugins.
where openclaw.cmd >nul 2>nul
if not errorlevel 1 (
  call openclaw.cmd gateway run
  exit /b %ERRORLEVEL%
)
call openclaw gateway run
exit /b %ERRORLEVEL%
