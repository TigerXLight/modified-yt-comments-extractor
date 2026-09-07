@echo off
setlocal
cd /d "%~dp0..\.." >nul 2>nul
cd /d "%CD%"
echo [R42DE] Building post-marketplace-all OpenClaw reference ZIP...
call tools\webview2_source_role_editor_native\_r42de_python.cmd profile_media_openclaw_full_suite_installer_r42de.py build-reference-zip
exit /b %ERRORLEVEL%
