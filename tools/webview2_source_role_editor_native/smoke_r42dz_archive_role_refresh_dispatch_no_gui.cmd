@echo off
setlocal
echo [R42DZ] Running no-GUI archive role-refresh dispatch smoke tests...
call "%~dp0_r42dz_python.cmd" -m py_compile profile_media_archive_role_refresh_dispatch_r42dz.py || exit /b 1
call "%~dp0_r42dz_python.cmd" profile_media_archive_role_refresh_dispatch_r42dz.py --self-test || exit /b 1
echo [R42DZ] Checking Program.cs no-navigation refresh guard...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p='tools\webview2_source_role_editor_native\Program.cs'; $t=Get-Content -LiteralPath $p -Raw; $ok=($t -like '*r42dz_role_overlay_refresh_deferred_no_navigation*') -and ($t -like '*YTCE_R42DZ_ALLOW_ROLE_REFRESH_NAVIGATION*') -and ($t -like '*role_overlay_refresh*'); if(-not $ok){ throw 'R42DZ Program.cs guard marker missing.' }; Write-Host '[DONE] R42DZ Program.cs guard markers present.'"
echo [R42DZ] Building native WebView2 helper with no-navigation role-refresh guard...
dotnet build tools\webview2_source_role_editor_native\YTCE.NativeSourceRoleEditor.csproj -c Release || exit /b 1
echo [DONE] R42DZ smoke/build passed.
endlocal
