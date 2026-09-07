@echo off
setlocal EnableExtensions
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%..\.." >nul || exit /b 1
set "ROOT=%CD%"
popd >nul
set "OUT=%ROOT%\profile_media_live_captures\link_source_role_webview_overlay"
set "BUILDOUT=%OUT%\r42aw_native_editor_build"

if "%ROOT%"=="" (
  echo ERROR: ROOT was not resolved.
  exit /b 1
)

echo ===== R42AW/R42AI native WebView2 source-role editor build =====
echo ROOT    : %ROOT%
echo BUILDOUT: %BUILDOUT%

dotnet restore "%SCRIPT_DIR%YTCE.NativeSourceRoleEditor.csproj"
if errorlevel 1 exit /b 1

dotnet publish "%SCRIPT_DIR%YTCE.NativeSourceRoleEditor.csproj" -c Release -o "%BUILDOUT%" --self-contained false /p:UseAppHost=true
if errorlevel 1 exit /b 1

echo.
echo ===== built helper files =====
dir /B "%BUILDOUT%\YTCE.NativeSourceRoleEditor.R42AW.*"
