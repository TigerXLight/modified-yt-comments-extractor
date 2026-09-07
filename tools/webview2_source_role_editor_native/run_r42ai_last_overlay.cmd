@echo off
setlocal EnableExtensions
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%..\.." >nul || exit /b 1
set "ROOT=%CD%"
popd >nul
set "OUT=%ROOT%\profile_media_live_captures\link_source_role_webview_overlay"
set "BUILDOUT=%OUT%\r42ar_native_editor_build"
set "PAYLOAD=%OUT%\selected_link_source_role_overlay.json"
set "CHANGES=%OUT%\selected_link_source_role_overlay_changes.jsonl"
set "LOG=%OUT%\selected_link_source_role_native_webview2_launch.log"
set "UDF=%LOCALAPPDATA%\YTCE\WebView2SourceRoleEditor"
set "EXE=%BUILDOUT%\YTCE.NativeSourceRoleEditor.R42AR.exe"

echo ===== R42AR/R42AI native WebView2 source-role editor last-overlay run =====
echo ROOT   : %ROOT%
echo PAYLOAD: %PAYLOAD%
echo UDF    : %UDF%
echo LOG    : %LOG%

if not exist "%PAYLOAD%" (
  echo ERROR: last overlay payload not found. Open a selected source once from the app first.
  exit /b 2
)

if not exist "%EXE%" (
  call "%SCRIPT_DIR%build_r42ai_native_source_role_editor.cmd"
  if errorlevel 1 exit /b 1
)

for /f "usebackq delims=" %%U in (`powershell -NoProfile -Command "$p=$env:PAYLOAD; $j=Get-Content -LiteralPath $p -Raw ^| ConvertFrom-Json; [Console]::Write($j.selected_url)"`) do set "URL=%%U"
if "%URL%"=="" set "URL=https://metro.co.uk/2026/07/17/people-shout-seagull-eater-street-far-right-lies-29157396/"

echo Launching: %EXE%
"%EXE%" --root "%ROOT%" --payload "%PAYLOAD%" --url "%URL%" --udf "%UDF%" --changes "%CHANGES%" --log "%LOG%" --mode semantic

echo.
echo ===== latest R42AI/R42AR native timing log =====
powershell -NoProfile -Command "if(Test-Path -LiteralPath '%LOG%'){ Get-Content -LiteralPath '%LOG%' -Tail 160 } else { Write-Host 'No log found.' }"
