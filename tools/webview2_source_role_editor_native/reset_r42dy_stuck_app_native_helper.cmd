@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%" || exit /b 1
echo [R42DY] Stopping only project app/native helper processes, no archive/browser launch...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$root=(Get-Location).Path; Get-CimInstance Win32_Process | Where-Object { ($_.CommandLine -like '*main.py*' -and $_.CommandLine -like '*Modified YouTube comment extractor*') -or ($_.CommandLine -like '*YTCE.NativeSourceRoleEditor.R42CR*' -and $_.CommandLine -like '*Modified YouTube comment extractor*') } | ForEach-Object { Write-Host ('Stopping PID ' + $_.ProcessId + ' ' + $_.Name); Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
echo [DONE] R42DY reset complete.
endlocal
