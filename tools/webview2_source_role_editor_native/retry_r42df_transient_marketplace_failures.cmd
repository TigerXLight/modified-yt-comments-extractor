@echo off
setlocal
cd /d "%~dp0..\.."
if /i not "%~1"=="YES" (
  echo [FAIL] This retries non-symlink transient OpenClaw marketplace failures.
  echo        Re-run as: tools\webview2_source_role_editor_native\retry_r42df_transient_marketplace_failures.cmd YES
  exit /b 2
)
echo [R42DF] Retrying transient/non-permission marketplace failures...
call tools\webview2_source_role_editor_native\_r42df_python.cmd profile_media_openclaw_failed_marketplace_retry_r42df.py retry_transient YES
exit /b %ERRORLEVEL%
