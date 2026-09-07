@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42EB] Running archive role local-fixture URL guard smoke tests...
call "%~dp0_r42eb_python.cmd" profile_media_archive_role_local_fixture_r42eb.py --self-test || exit /b 1
call "%~dp0_r42eb_python.cmd" profile_media_archive_role_local_fixture_r42eb_test.py || exit /b 1
echo [R42EB] Checking Program.cs / overlay markers...
call "%~dp0_r42eb_python.cmd" -c "from pathlib import Path; import json; root=Path.cwd(); p=(root/'tools/webview2_source_role_editor_native/Program.cs').read_text(encoding='utf-8', errors='replace'); o=(root/'profile_media_link_source_real_webview_overlay_v83d.py').read_text(encoding='utf-8', errors='replace'); d={'program_markdown_guard':'R42EB: tolerate chat/Markdown-wrapped URLs' in p,'program_bad_case_guard':'https://archive.ph/6Mr3C' in p and 'https://archive.ph/6mr3C' in p,'program_url_clean_assignment':'_url = CleanNativeUrl(FirstNonBlank(' in p and '_urlArg = CleanNativeUrl(GetString(\"url\"))' in p,'overlay_guard_marker':'R42EB_ARCHIVE_URL_GUARD_MARKER' in o,'overlay_cleaner':'_r42eb_clean_url_for_navigation' in o}; print(json.dumps(d, indent=2)); raise SystemExit(0 if all(d.values()) else 1)" || exit /b 1
where dotnet >nul 2>nul
if %ERRORLEVEL%==0 (
  echo [R42EB] Building native WebView2 helper with URL guard...
  dotnet build "tools\webview2_source_role_editor_native\YTCE.NativeSourceRoleEditor.csproj" -c Release || exit /b 1
) else (
  echo [WARN] dotnet not on PATH; skipped native compile check.
)
echo [DONE] R42EB smoke/build passed.
