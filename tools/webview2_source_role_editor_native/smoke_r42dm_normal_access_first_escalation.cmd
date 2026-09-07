@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42DM] Running normal-access-first restricted-access escalation smoke tests...
call tools\webview2_source_role_editor_native\_r42dm_python.cmd profile_media_access_escalation_policy_r42dm_test.py
if errorlevel 1 exit /b %ERRORLEVEL%
call tools\webview2_source_role_editor_native\_r42dm_python.cmd -m py_compile profile_media_access_escalation_policy_r42dm.py profile_media_universal_source_link_adapter_r42dk.py profile_media_universal_source_link_adapter_r42dl.py source_adapters.py source_resource_state.py main.py
if errorlevel 1 exit /b %ERRORLEVEL%
echo [DONE] R42DM smoke passed.
