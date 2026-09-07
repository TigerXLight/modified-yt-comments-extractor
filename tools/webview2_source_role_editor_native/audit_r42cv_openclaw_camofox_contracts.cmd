@echo off
setlocal EnableExtensions
cd /d "%~dp0..\.."
set "ROOT=%CD%"
set "OUT=%ROOT%\profile_media_live_captures\r42cv_openclaw_camofox"
mkdir "%OUT%" 2>nul
"C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe" "%ROOT%\profile_media_openclaw_camofox_bridge_r42cv.py" > "%OUT%\openclaw_contract_audit_stdout.json" 2> "%OUT%\openclaw_contract_audit_stderr.txt"
set "RC=%ERRORLEVEL%"
echo [DONE] R42CW OpenClaw/camofox contract audit output: "%OUT%"
exit /b %RC%
