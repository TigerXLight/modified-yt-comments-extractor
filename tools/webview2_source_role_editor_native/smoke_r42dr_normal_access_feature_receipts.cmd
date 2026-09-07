@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42DR] Running normal-access feature receipt + R42DQ worker-route smoke tests...
call tools\webview2_source_role_editor_native\_r42dr_python.cmd -m py_compile profile_media_normal_access_feature_receipts_r42dr.py profile_media_normal_access_feature_receipts_r42dr_test.py profile_media_normal_access_provider_layer_r42dq.py profile_media_universal_worker_source_router_r42do.py
if errorlevel 1 exit /b 1
call tools\webview2_source_role_editor_native\_r42dr_python.cmd profile_media_normal_access_feature_receipts_r42dr_test.py
if errorlevel 1 exit /b 1
echo [DONE] R42DR smoke passed without pytest.
exit /b 0
