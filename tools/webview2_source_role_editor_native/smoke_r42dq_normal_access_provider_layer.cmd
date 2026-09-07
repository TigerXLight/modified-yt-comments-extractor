@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42DQ] Running normal access/browser/provider layer smoke tests...
call "%~dp0_r42dq_python.cmd" profile_media_normal_access_provider_layer_r42dq_test.py
if errorlevel 1 exit /b %ERRORLEVEL%
call "%~dp0_r42dq_python.cmd" -m py_compile profile_media_normal_access_provider_layer_r42dq.py main.py
if errorlevel 1 exit /b %ERRORLEVEL%
echo [DONE] R42DQ smoke passed without pytest.
