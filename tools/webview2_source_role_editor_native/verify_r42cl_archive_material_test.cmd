@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0..\.." || exit /b 1
set "ROOT=%CD%"
set "MARKER=%ROOT%\profile_media_live_captures\r42cl_clean_archive_material_test_start.json"
for /f "tokens=1-4 delims=/-. " %%a in ("%date%") do set "D=%%d%%b%%c"
for /f "tokens=1-4 delims=:. " %%a in ("%time%") do set "T=%%a%%b%%c"
set "T=%T: =0%"
set "STAMP=%D%_%T%"
set "OUT=%USERPROFILE%\Downloads\r42cl_archive_material_test_audit_%STAMP%.txt"

echo Writing audit to: %OUT%

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Continue'; $root=(Get-Location).Path; $marker=Join-Path $root 'profile_media_live_captures\r42cl_clean_archive_material_test_start.json'; $out='%OUT%'; $data=$null; if(Test-Path -LiteralPath $marker){ $data=Get-Content -LiteralPath $marker -Raw | ConvertFrom-Json; $since=[datetime]$data.started_at } else { $since=(Get-Date).AddHours(-2) }; $base=Join-Path $root 'profile_media_live_captures'; '===== R42CL ARCHIVE MATERIAL CLEAN TEST AUDIT =====' | Set-Content -LiteralPath $out -Encoding UTF8; ('Root: ' + $root) | Add-Content -LiteralPath $out; ('Since: ' + $since.ToString('o')) | Add-Content -LiteralPath $out; ('Target: https://archive.ph/6mr3C') | Add-Content -LiteralPath $out; '' | Add-Content -LiteralPath $out; '===== RECENT FILES CONTAINING TARGET URL/TITLE =====' | Add-Content -LiteralPath $out; $needles=@('https://archive.ph/6mr3C','archive.ph/6mr3C','People shout "seagull eater"','seagull eater','Muslim woman who far right painted'); $files=Get-ChildItem -LiteralPath $base -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -ge $since -and $_.Length -lt 50000000 }; $hitCount=0; foreach($f in $files){ try { $m=Select-String -LiteralPath $f.FullName -Pattern $needles -SimpleMatch -ErrorAction Stop | Select-Object -First 8; if($m){ $hitCount++; ('--- FILE: ' + $f.FullName) | Add-Content -LiteralPath $out; ('    LastWriteTime: ' + $f.LastWriteTime.ToString('o') + ' Size: ' + $f.Length) | Add-Content -LiteralPath $out; foreach($x in $m){ ('    L' + $x.LineNumber + ': ' + $x.Line) | Add-Content -LiteralPath $out } } } catch {} }; ('Recent matching file count: ' + $hitCount) | Add-Content -LiteralPath $out; '' | Add-Content -LiteralPath $out; '===== ROLEPLAN SQLITE CHECK =====' | Add-Content -LiteralPath $out; $db=Join-Path $base 'link_source_role_webview_overlay\selected_link_source_role_roleplan.sqlite'; if(Test-Path -LiteralPath $db){ ('DB: ' + $db) | Add-Content -LiteralPath $out } else { 'DB: missing' | Add-Content -LiteralPath $out }; Write-Host 'Audit text written:' $out"

set "PY=C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" -c "import sqlite3, pathlib, os; root=pathlib.Path(os.getcwd()); out=pathlib.Path(os.path.expanduser('~'))/'Downloads'/'%~nx0.tmp'; print('python ok')" >nul 2>nul
if errorlevel 1 goto no_python

"%PY%" - <<PY >> "%OUT%" 2>&1
import sqlite3, pathlib, json, os
root = pathlib.Path.cwd()
base = root / 'profile_media_live_captures'
db = base / 'link_source_role_webview_overlay' / 'selected_link_source_role_roleplan.sqlite'
print('')
print('===== SQLITE SOURCE URL COUNTS =====')
if not db.exists():
    print('DB missing:', db)
else:
    con = sqlite3.connect(str(db))
    cur = con.cursor()
    for table, col in [('role_source_sessions','selected_url'), ('role_plan_current','selected_url'), ('role_latest','selected_url'), ('role_plan_rows','url')]:
        try:
            print('---', table)
            for row in cur.execute(f"select {col}, count(*) from {table} group by {col} order by count(*) desc"):
                print(row[0], row[1])
        except Exception as e:
            print(table, 'ERROR', e)
    print('')
    print('===== ARCHIVE.PH ROW SAMPLE =====')
    try:
        for row in cur.execute("select mode,row_index,role,substr(text,1,160),url,media_url from role_plan_rows where url like '%archive.ph/6mr3C%' or media_url like '%archive.ph/6mr3C%' limit 25"):
            print(row)
    except Exception as e:
        print('archive row sample error:', e)
    con.close()
PY

goto done

:no_python
echo.>> "%OUT%"
echo Python was not available for sqlite inspection.>> "%OUT%"

:done
echo.
echo Done. Upload this audit if needed:
echo %OUT%
