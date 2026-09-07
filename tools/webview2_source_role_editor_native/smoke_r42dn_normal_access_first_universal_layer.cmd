@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42DN] Running normal-access-first universal source/link layer smoke tests...
call "%~dp0_r42dn_python.cmd" profile_media_normal_access_layer_r42dn_test.py
if errorlevel 1 exit /b %ERRORLEVEL%
call "%~dp0_r42dn_python.cmd" -m py_compile profile_media_normal_access_layer_r42dn.py profile_media_universal_source_link_adapter_r42dk.py profile_media_universal_source_link_adapter_r42dl.py profile_media_access_escalation_policy_r42dm.py
if errorlevel 1 exit /b %ERRORLEVEL%
echo [DONE] R42DN smoke passed.
