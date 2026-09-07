@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42DM] Building normal-access-first escalation reference ZIP...
call tools\webview2_source_role_editor_native\probe_r42dm_normal_access_first_escalation.cmd
set "STAMP=%DATE:~-4%%DATE:~3,2%%DATE:~0,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
set "STAMP=%STAMP: =0%"
set "OUTROOT=profile_media_live_captures\r42dm_normal_access_first_escalation"
set "STAGE=%TEMP%\r42dm_normal_access_first_escalation_%STAMP%"
set "ZIP=%CD%\%OUTROOT%\r42dm_normal_access_first_escalation_%STAMP%.zip"
if exist "%STAGE%" rmdir /s /q "%STAGE%"
mkdir "%STAGE%\project" >nul
copy /y "profile_media_access_escalation_policy_r42dm.py" "%STAGE%\project\" >nul
copy /y "profile_media_access_escalation_policy_r42dm_test.py" "%STAGE%\project\" >nul
copy /y "profile_media_universal_source_link_adapter_r42dk.py" "%STAGE%\project\" >nul
copy /y "profile_media_universal_source_link_adapter_r42dl.py" "%STAGE%\project\" >nul
copy /y "source_adapters.py" "%STAGE%\project\" >nul
copy /y "source_resource_state.py" "%STAGE%\project\" >nul
copy /y "main.py" "%STAGE%\project\" >nul
copy /y "R42DM_NORMAL_ACCESS_FIRST_ESCALATION_NOTES_20260906.md" "%STAGE%\project\" >nul
mkdir "%STAGE%\project\tools\webview2_source_role_editor_native" >nul
copy /y "tools\webview2_source_role_editor_native\_r42dm_python.cmd" "%STAGE%\project\tools\webview2_source_role_editor_native\" >nul
copy /y "tools\webview2_source_role_editor_native\smoke_r42dm_normal_access_first_escalation.cmd" "%STAGE%\project\tools\webview2_source_role_editor_native\" >nul
copy /y "tools\webview2_source_role_editor_native\probe_r42dm_normal_access_first_escalation.cmd" "%STAGE%\project\tools\webview2_source_role_editor_native\" >nul
copy /y "tools\webview2_source_role_editor_native\build_r42dm_normal_access_first_escalation_zip.cmd" "%STAGE%\project\tools\webview2_source_role_editor_native\" >nul
copy /y "tools\webview2_source_role_editor_native\make_r42dm_active_access_source_upload_zip.cmd" "%STAGE%\project\tools\webview2_source_role_editor_native\" >nul
xcopy /s /e /i /y "%OUTROOT%" "%STAGE%\_r42dm_probe_outputs" >nul 2>nul
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path '%STAGE%\*' -DestinationPath '%ZIP%' -Force"
if errorlevel 1 exit /b %ERRORLEVEL%
for %%F in ("%ZIP%") do copy /y "%ZIP%" "%USERPROFILE%\Downloads\%%~nxF" >nul
echo [DONE] Created ZIP: %ZIP%
for %%F in ("%ZIP%") do echo [DONE] Copied ZIP to Downloads: %USERPROFILE%\Downloads\%%~nxF
