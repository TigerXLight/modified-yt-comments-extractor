@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42DP] Building active worker/account-channel source upload ZIP...
call "%~dp0_r42dp_python.cmd" -c "from pathlib import Path; from datetime import datetime; import zipfile, shutil; root=Path.cwd(); stamp=datetime.now().strftime('%Y%m%d_%H%M%S'); out_root=root/'profile_media_live_captures'/'r42dp_account_channel_worker_adapter'; out_root.mkdir(parents=True, exist_ok=True); zip_path=out_root/f'r42dp_active_worker_account_channel_source_upload_{stamp}.zip'; patterns=['main.py','source_adapters.py','source_resource_state.py','profile_media_*r42d*.py','R42D*_*.md','tools/webview2_source_role_editor_native/*r42d*.cmd']; seen=set(); z=zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED); [ (z.write(p,'project/'+str(p.relative_to(root)).replace('\\\\','/')), seen.add(p)) for pat in patterns for p in root.glob(pat) if p.is_file() and p not in seen and p.stat().st_size<=8000000 ]; z.close(); downloads=Path.home()/'Downloads'/zip_path.name; shutil.copy2(zip_path, downloads); print('[DONE] Created ZIP:', zip_path); print('[DONE] Copied ZIP to Downloads:', downloads); print('[DONE] Files included:', len(seen))"
exit /b %ERRORLEVEL%
