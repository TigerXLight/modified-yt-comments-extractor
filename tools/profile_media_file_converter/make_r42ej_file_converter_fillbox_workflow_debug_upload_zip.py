from __future__ import annotations
from pathlib import Path
import json, os, shutil, zipfile
from datetime import datetime
ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUT_DIR = ROOT / "profile_media_live_captures" / "r42ej_file_converter_fillbox_workflow"
OUT_DIR.mkdir(parents=True, exist_ok=True)
zip_path = OUT_DIR / f"r42ej_file_converter_fillbox_workflow_debug_upload_{STAMP}.zip"
downloads = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Downloads" / zip_path.name
files = [
    ROOT / "main.py",
    ROOT / "profile_media_file_converter_r42eh.py",
    ROOT / "profile_media_file_converter_r42eg.py",
    ROOT / "profile_media_file_converter_r42eh_test.py",
    ROOT / "R42EJ_FILE_CONVERTER_FILLBOX_WORKFLOW_NOTES_20260908.md",
    ROOT / "assets" / "Keep icon icons8-kappa-100.png",
    ROOT / "assets" / "Open folder icon icons8-opened-folder-ios-27-outlined.png",
    ROOT / "tools" / "profile_media_file_converter" / "smoke_r42ej_file_converter_fillbox_workflow.cmd",
    ROOT / "tools" / "profile_media_file_converter" / "probe_r42ej_file_converter_fillbox_workflow_no_gui.py",
    ROOT / "tools" / "profile_media_file_converter" / "probe_r42ej_file_converter_fillbox_workflow_no_gui.cmd",
    ROOT / "profile_media_live_captures" / "r42ej_file_converter_fillbox_workflow" / "r42ej_file_converter_fillbox_workflow_probe_summary.json",
]
included=[]
with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
    for p in files:
        if p.exists() and p.is_file():
            arc = p.relative_to(ROOT).as_posix()
            zf.write(p, arc)
            included.append(arc)
try:
    shutil.copy2(zip_path, downloads)
except Exception:
    downloads = Path("")
payload={"schema":"ytce.r42ej.file_converter_fillbox_workflow.v1.debug_zip","zip_path":str(zip_path),"downloads_zip_path":str(downloads),"included_files":len(included),"included":included,"side_effects":{"archive_ph_hit":False,"network_actions_performed":False,"native_webview2_started":False,"app_started":False},"verdict":{"zip_created":zip_path.exists(),"ready_for_upload":zip_path.exists()}}
print(json.dumps(payload, indent=2, ensure_ascii=False))
print(f"[DONE] Created ZIP: {zip_path}")
if downloads:
    print(f"[DONE] Copied ZIP to Downloads: {downloads}")
