from __future__ import annotations
import os, zipfile
from datetime import datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
out = ROOT / "profile_media_live_captures" / f"r42fe_target_size_cap_retry_debug_{stamp}.zip"
out.parent.mkdir(parents=True, exist_ok=True)
files = [
    "main.py",
    "profile_media_file_converter_r42eh.py",
    "R42FE_TARGET_SIZE_CAP_RETRY_NOTES_20260910.md",
    "tools/profile_media_file_converter/smoke_r42fe_target_size_cap_retry.cmd",
    "tools/profile_media_file_converter/probe_r42fe_target_size_cap_retry_no_gui.py",
    "tools/profile_media_file_converter/probe_r42fe_target_size_cap_retry_no_gui.cmd",
    "tools/profile_media_file_converter/audit_r42fe_target_size_cap_retry_no_gui.py",
    "tools/profile_media_file_converter/audit_r42fe_target_size_cap_retry_no_gui.cmd",
]
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for rel in files:
        p = ROOT / rel
        if p.exists():
            z.write(p, rel)
print(out)
