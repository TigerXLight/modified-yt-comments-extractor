@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42DP] Running account/channel worker adapter + archive CLI fix smoke tests...
call "%~dp0_r42dp_python.cmd" profile_media_account_channel_worker_adapter_r42dp.py --self-test
if errorlevel 1 exit /b %ERRORLEVEL%
call "%~dp0_r42dp_python.cmd" -m py_compile profile_media_account_channel_worker_adapter_r42dp.py profile_media_universal_worker_source_router_r42do.py main.py
if errorlevel 1 exit /b %ERRORLEVEL%
echo [DONE] R42DP smoke passed.
