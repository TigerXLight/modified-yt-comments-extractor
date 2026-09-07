@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42DR] Probing normal access/browser/provider receipts and worker route alignment...
set "OUT=profile_media_live_captures\r42dr_normal_access_feature_receipts\probe_%DATE:~-4%%DATE:~3,2%%DATE:~0,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
set "OUT=%OUT: =0%"
call tools\webview2_source_role_editor_native\_r42dr_python.cmd profile_media_normal_access_feature_receipts_r42dr.py --probe --output-dir "%OUT%"
if errorlevel 1 exit /b 1
echo [DONE] Probe output: %OUT%
exit /b 0
