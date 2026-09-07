@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
echo [R42DX] Stopping only YTCE main.py and native source-role helper processes...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$root=(Resolve-Path -LiteralPath '%ROOT%').Path; $procs=Get-CimInstance Win32_Process | Where-Object { ($_.CommandLine -like '*main.py*' -and $_.CommandLine -like ('*' + $root.Replace('\','\\') + '*')) -or ($_.CommandLine -like '*YTCE.NativeSourceRoleEditor.R42CR*' -and $_.CommandLine -like ('*' + $root.Replace('\','\\') + '*')) }; foreach($p in $procs){ Write-Host ('Stopping PID ' + $p.ProcessId + ' : ' + $p.Name); Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }; if(-not $procs){ Write-Host 'No matching YTCE app/helper process found.' }"
call "%~dp0reset_r42dw_native_webview2_server.cmd" 2>nul
echo [DONE] R42DX reset complete.
endlocal
