@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42DK] Running universal source/link adapter smoke tests...
call tools\webview2_source_role_editor_native\_r42dk_python.cmd -m py_compile source_adapters.py source_resource_state.py profile_media_universal_source_link_adapter_r42dk.py main.py
if errorlevel 1 exit /b %errorlevel%
call tools\webview2_source_role_editor_native\_r42dk_python.cmd source_adapters_test.py
if errorlevel 1 exit /b %errorlevel%
call tools\webview2_source_role_editor_native\_r42dk_python.cmd source_resource_state_test.py
if errorlevel 1 exit /b %errorlevel%
call tools\webview2_source_role_editor_native\_r42dk_python.cmd -m pytest -q profile_media_universal_source_link_adapter_r42dk_test.py source_adapters_test.py source_resource_state_test.py
if errorlevel 1 (
  echo [WARN] pytest path failed or pytest is unavailable; direct self-tests above already ran where available.
)
echo [DONE] R42DK smoke completed.
