@echo off
setlocal
if "%~1"=="" (
  echo Usage: decide_r42dj_source_route.cmd ^<source-or-url^> [source-kind]
  exit /b 2
)
set "SRC=%~1"
set "KIND=%~2"
if "%KIND%"=="" set "KIND=auto"
pushd "%~dp0..\.." || exit /b 1
call tools\webview2_source_role_editor_native\_r42dj_python.cmd profile_media_openclaw_source_adapter_bridge_r42dj.py --mode decide --source "%SRC%" --source-kind "%KIND%"
set "RC=%ERRORLEVEL%"
popd
exit /b %RC%
