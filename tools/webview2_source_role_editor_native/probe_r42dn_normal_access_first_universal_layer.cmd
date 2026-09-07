@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42DN] Probing normal access/browser/provider layer vs restricted Tor/Camoufox fallback...
set "OUT=profile_media_live_captures\r42dn_normal_access_first_universal_layer\probe_%DATE:~-4%%DATE:~3,2%%DATE:~0,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
set "OUT=%OUT: =0%"
call "%~dp0_r42dn_python.cmd" profile_media_normal_access_layer_r42dn.py --probe --output-dir "%OUT%"
if errorlevel 1 exit /b %ERRORLEVEL%
echo [DONE] Probe output: %OUT%
