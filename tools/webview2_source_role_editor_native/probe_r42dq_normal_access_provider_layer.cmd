@echo off
setlocal
cd /d "%~dp0..\.."
set "OUT=profile_media_live_captures\r42dq_normal_access_provider_layer\probe_%DATE:~-4%%DATE:~3,2%%DATE:~0,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
set "OUT=%OUT: =0%"
echo [R42DQ] Probing normal access/browser/provider features...
call "%~dp0_r42dq_python.cmd" profile_media_normal_access_provider_layer_r42dq.py --probe --output-dir "%OUT%"
if errorlevel 1 exit /b %ERRORLEVEL%
echo [DONE] Probe output: %OUT%
