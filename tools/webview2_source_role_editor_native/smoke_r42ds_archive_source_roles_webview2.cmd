@echo off
setlocal
cd /d "%~dp0\..\.."
echo [R42DS] Running archive source-role WebView2 surface smoke tests...
call tools\webview2_source_role_editor_native\_r42ds_python.cmd -m py_compile profile_media_archive_source_role_surface_r42ds.py main.py
if errorlevel 1 exit /b 1
call tools\webview2_source_role_editor_native\_r42ds_python.cmd profile_media_archive_source_role_surface_r42ds_test.py
if errorlevel 1 exit /b 1
echo [DONE] R42DS smoke passed without pytest.
endlocal
