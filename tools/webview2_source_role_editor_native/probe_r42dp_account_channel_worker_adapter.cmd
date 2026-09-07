@echo off
setlocal
cd /d "%~dp0..\.."
set "OUT=profile_media_live_captures\r42dp_account_channel_worker_adapter\probe_%DATE:~-4%%DATE:~3,2%%DATE:~0,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
set "OUT=%OUT: =0%"
echo [R42DP] Probing account/channel worker adapter receipts...
call "%~dp0_r42dp_python.cmd" profile_media_account_channel_worker_adapter_r42dp.py --probe --output-dir "%OUT%"
if errorlevel 1 exit /b %ERRORLEVEL%
echo [R42DP] Probing R42DO direct archive route after CLI auto-owner fix...
call "%~dp0_r42do_python.cmd" profile_media_universal_worker_source_router_r42do.py "https://archive.ph/6mr3C" webpage archive_cli_fix --output-dir "%OUT%\archive_cli_fix"
if errorlevel 1 exit /b %ERRORLEVEL%
echo [DONE] Probe output: %OUT%
