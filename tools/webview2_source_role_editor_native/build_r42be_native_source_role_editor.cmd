@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "OUT=%ROOT%\profile_media_live_captures\link_source_role_webview_overlay\r42be_native_editor_build"
echo ===== R42BE/R42AI native WebView2 source-role editor build =====
echo ROOT    : %ROOT%
echo BUILDOUT: %OUT%
if not exist "%OUT%" mkdir "%OUT%"
pushd "%~dp0"
dotnet restore YTCE.NativeSourceRoleEditor.csproj || exit /b 1
dotnet publish YTCE.NativeSourceRoleEditor.csproj -c Release -o "%OUT%" --self-contained false /p:UseAppHost=true || exit /b 1
popd
echo.
echo ===== built helper files =====
dir /b "%OUT%\YTCE.NativeSourceRoleEditor.R42BE.*"
endlocal
