@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42DO] Running universal worker source-router smoke tests...
call "%~dp0_r42do_python.cmd" profile_media_universal_worker_source_router_r42do_test.py
if errorlevel 1 exit /b %ERRORLEVEL%
call "%~dp0_r42do_python.cmd" -m py_compile profile_media_universal_worker_source_router_r42do.py profile_media_normal_access_layer_r42dn.py profile_media_access_escalation_policy_r42dm.py profile_media_universal_source_link_adapter_r42dk.py profile_media_universal_source_link_adapter_r42dl.py main.py
if errorlevel 1 exit /b %ERRORLEVEL%
echo [DONE] R42DO smoke passed.
