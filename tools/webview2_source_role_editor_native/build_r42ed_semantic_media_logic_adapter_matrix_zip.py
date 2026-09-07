from __future__ import annotations

from pathlib import Path
from datetime import datetime
import json
import os
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = ROOT / "profile_media_live_captures" / "r42ed_semantic_media_logic_adapter_matrix"
DOWNLOADS = Path.home() / "Downloads"

INCLUDE_ROOT_FILES = [
    "profile_media_semantic_media_logic_matrix_r42ed.py",
    "profile_media_semantic_media_logic_matrix_r42ed_test.py",
    "profile_media_archive_role_payload_r42dw.py",
    "R42ED_SEMANTIC_MEDIA_LOGIC_ADAPTER_MATRIX_NOTES_20260907.md",
]
INCLUDE_TOOL_FILES = [
    "Program.cs",
    "YTCE.NativeSourceRoleEditor.csproj",
    "_r42ed_python.cmd",
    "reset_r42ed_stuck_app_native_helper.cmd",
    "smoke_r42ed_semantic_media_logic_adapter_matrix.cmd",
    "probe_r42ed_semantic_media_logic_adapter_matrix_no_gui.cmd",
    "probe_r42ed_semantic_media_logic_adapter_matrix_no_gui_recolor.cmd",
    "probe_r42ed_semantic_media_logic_adapter_matrix_no_gui.py",
    "build_r42ed_semantic_media_logic_adapter_matrix_zip.cmd",
    "build_r42ed_semantic_media_logic_adapter_matrix_zip.py",
    "make_r42ed_semantic_media_logic_adapter_matrix_debug_upload_zip.cmd",
    "make_r42ed_semantic_media_logic_adapter_matrix_debug_upload_zip.py",
]


def add_file(zf: zipfile.ZipFile, src: Path, arc: str) -> bool:
    if not src.is_file():
        return False
    zf.write(src, arc)
    return True


def main() -> int:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    # Run a fresh no-GUI matrix probe first, but do not fail the ZIP build if no prior payload exists.
    probe_cmd = [sys.executable, str(ROOT / "tools" / "webview2_source_role_editor_native" / "probe_r42ed_semantic_media_logic_adapter_matrix_no_gui.py")]
    try:
        subprocess.run(probe_cmd, cwd=str(ROOT), check=False, shell=False)
    except Exception:
        pass
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = OUT_ROOT / f"r42ed_semantic_media_logic_adapter_matrix_{stamp}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        manifest = {"schema": "ytce.r42ed.semantic_media_logic_adapter_matrix.reference_zip.v1", "created_at_local": datetime.now().replace(microsecond=0).isoformat(), "included": []}
        for rel in INCLUDE_ROOT_FILES:
            if add_file(zf, ROOT / rel, rel):
                manifest["included"].append(rel)
        tool_base = ROOT / "tools" / "webview2_source_role_editor_native"
        for name in INCLUDE_TOOL_FILES:
            arc = "tools/webview2_source_role_editor_native/" + name
            if add_file(zf, tool_base / name, arc):
                manifest["included"].append(arc)
        # Include latest generated matrix outputs and payload summaries, bounded.
        generated = sorted(OUT_ROOT.rglob("r42ed_*"), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)[:80]
        for p in generated:
            if p.is_file() and p.stat().st_size < 2_500_000:
                arc = "_runtime/" + p.relative_to(ROOT).as_posix()
                zf.write(p, arc)
                manifest["included"].append(arc)
        zf.writestr("r42ed_reference_zip_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    dst = DOWNLOADS / zip_path.name
    shutil.copy2(zip_path, dst)
    print(f"[DONE] Created ZIP: {zip_path}")
    print(f"[DONE] Copied ZIP to Downloads: {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
