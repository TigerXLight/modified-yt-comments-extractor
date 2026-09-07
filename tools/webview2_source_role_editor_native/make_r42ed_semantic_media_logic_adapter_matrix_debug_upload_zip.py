from __future__ import annotations

from pathlib import Path
from datetime import datetime
import json
import shutil
import zipfile
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = ROOT / "profile_media_live_captures" / "r42ed_semantic_media_logic_adapter_matrix"
DOWNLOADS = Path.home() / "Downloads"


def main() -> int:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run([sys.executable, str(ROOT / "tools" / "webview2_source_role_editor_native" / "probe_r42ed_semantic_media_logic_adapter_matrix_no_gui.py")], cwd=str(ROOT), check=False)
    except Exception:
        pass
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = OUT_ROOT / f"r42ed_semantic_media_logic_adapter_matrix_debug_upload_{stamp}.zip"
    included = []
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        roots = [
            ROOT / "profile_media_semantic_media_logic_matrix_r42ed.py",
            ROOT / "profile_media_semantic_media_logic_matrix_r42ed_test.py",
            ROOT / "profile_media_archive_role_payload_r42dw.py",
            ROOT / "R42ED_SEMANTIC_MEDIA_LOGIC_ADAPTER_MATRIX_NOTES_20260907.md",
            ROOT / "tools" / "webview2_source_role_editor_native" / "Program.cs",
        ]
        for p in roots:
            if p.is_file():
                arc = p.relative_to(ROOT).as_posix()
                zf.write(p, arc); included.append(arc)
        for p in sorted(OUT_ROOT.rglob("*"), key=lambda x: x.stat().st_mtime if x.exists() else 0, reverse=True)[:160]:
            if p.is_file() and p.stat().st_size < 2_500_000:
                arc = "_runtime/" + p.relative_to(ROOT).as_posix()
                zf.write(p, arc); included.append(arc)
        zf.writestr("r42ed_debug_upload_manifest.json", json.dumps({"schema":"ytce.r42ed.debug_upload_manifest.v1","created_at_local":datetime.now().replace(microsecond=0).isoformat(),"files_included":len(included),"included":included}, ensure_ascii=False, indent=2))
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    dst = DOWNLOADS / zip_path.name
    shutil.copy2(zip_path, dst)
    print(f"[DONE] Created ZIP: {zip_path}")
    print(f"[DONE] Copied ZIP to Downloads: {dst}")
    print(f"[DONE] Files included: {len(included)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
