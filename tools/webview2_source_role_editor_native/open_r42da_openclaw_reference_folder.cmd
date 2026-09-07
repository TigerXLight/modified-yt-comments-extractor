@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."
if exist "profile_media_live_captures\r42da_openclaw_all_plugins_reference" (
  explorer "profile_media_live_captures\r42da_openclaw_all_plugins_reference"
) else (
  explorer "profile_media_live_captures"
)
endlocal
