from __future__ import annotations
import zipfile
from datetime import datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
out = ROOT / "profile_media_live_captures" / f"r42fc_converter_capability_import_hotfix_debug_{stamp}.zip"
out.parent.mkdir(parents=True, exist_ok=True)
files = [
    "main.py",
    "profile_media_file_converter_r42eh.py",
    "R42FC_CONVERTER_CAPABILITY_IMPORT_HOTFIX_NOTES_20260910.md",
    "tools/profile_media_file_converter/smoke_r42fc_converter_capability_import_hotfix.cmd",
    "tools/profile_media_file_converter/probe_r42fc_converter_capability_import_hotfix_no_gui.py",
    "tools/profile_media_file_converter/probe_r42fc_converter_capability_import_hotfix_no_gui.cmd",
    "tools/profile_media_file_converter/audit_r42fc_converter_end_to_end_capability_matrix_no_gui.py",
    "tools/profile_media_file_converter/audit_r42fc_converter_end_to_end_capability_matrix_no_gui.cmd",
]
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
    for rel in files:
        p = ROOT / rel
        if p.exists():
            zf.write(p, rel)
print(out)
