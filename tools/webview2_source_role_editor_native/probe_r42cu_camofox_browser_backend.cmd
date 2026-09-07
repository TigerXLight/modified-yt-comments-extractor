@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."
echo [R42CU] Project root: %CD%
echo [R42CU] Checking bundled camofox-browser server...
if not exist "tools\camofox_browser_backend_r42cu\jo_inc_camofox_browser\server.js" (
  echo [FAIL] bundled server.js missing
  exit /b 1
)
if not exist "tools\camofox_browser_backend_r42cu\jo_inc_camofox_browser\package.json" (
  echo [FAIL] bundled package.json missing
  exit /b 1
)
where node >nul 2>&1
if errorlevel 1 (
  echo [WARN] node.exe not on PATH. jo-inc/camofox-browser needs Node.js >=22 for managed server mode.
) else (
  echo [PASS] node found
  node --version
)
where npm >nul 2>&1
if errorlevel 1 (
  echo [WARN] npm not on PATH. First-run dependency install cannot run automatically.
) else (
  echo [PASS] npm found
  npm --version
)
set "PY=C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" -c "import py_compile; [py_compile.compile(p, doraise=True) for p in ['profile_media_access_backend_router_r42ct.py','profile_media_camofox_browser_server_backend_r42cu.py','profile_media_archive_material_chain_r42ct.py','profile_media_tor_camoufox_material_backend_r42ct.py']]; print('[PASS] R42CU Python backend files compile')"
if errorlevel 1 exit /b 1
echo [R42CU] Probe complete.
exit /b 0
