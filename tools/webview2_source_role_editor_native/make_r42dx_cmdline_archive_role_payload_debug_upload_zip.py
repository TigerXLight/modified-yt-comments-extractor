from __future__ import annotations
from pathlib import Path
from datetime import datetime
import json
import os
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUTROOT = ROOT / "profile_media_live_captures" / "r42dx_cmdline_archive_role_payload"
OUTROOT.mkdir(parents=True, exist_ok=True)

EXTS = {".py", ".cmd", ".json", ".jsonl", ".txt", ".log", ".md", ".cs", ".csproj"}


def add(zf: zipfile.ZipFile, src: Path, arc: str, manifest: list[dict]) -> None:
    if src.is_file() and src.stat().st_size <= 5_000_000:
        zf.write(src, arc)
        manifest.append({"path": arc, "bytes": src.stat().st_size})


def latest_dirs(base: Path, limit: int = 8) -> list[Path]:
    if not base.exists():
        return []
    dirs = [p for p in base.iterdir() if p.is_dir()]
    dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return dirs[:limit]


def main() -> int:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = OUTROOT / f"r42dx_cmdline_archive_role_payload_debug_upload_{stamp}.zip"
    manifest: list[dict] = []
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in [
            "main.py",
            "profile_media_archive_role_payload_r42dw.py",
            "profile_media_archive_source_role_surface_r42ds.py",
            "profile_media_link_source_real_webview_overlay_v83d.py",
            "profile_media_archive_material_chain_r42ct.py",
            "R42DX_CMDLINE_ARCHIVE_ROLE_PAYLOAD_NO_GUI_NOTES_20260907.md",
            "tools/webview2_source_role_editor_native/Program.cs",
            "tools/webview2_source_role_editor_native/YTCE.NativeSourceRoleEditor.csproj",
            "tools/webview2_source_role_editor_native/_r42dx_python.cmd",
            "tools/webview2_source_role_editor_native/probe_r42dx_archive_role_payload_no_gui.py",
            "tools/webview2_source_role_editor_native/probe_r42dw_archive_role_payload_from_latest.py",
        ]:
            add(zf, ROOT / rel, rel, manifest)
        # bounded runtime state only: no recursive whole-project copies
        runtime_bases = [
            ROOT / "profile_media_live_captures" / "r42ct_archive_source_material",
            ROOT / "profile_media_live_captures" / "r42ds_archive_source_roles_webview2",
            ROOT / "profile_media_live_captures" / "r42dw_archive_role_payload",
            ROOT / "profile_media_live_captures" / "r42dx_cmdline_archive_role_payload",
            ROOT / "profile_media_live_captures" / "link_source_role_webview_overlay",
        ]
        for base in runtime_bases:
            if base.name == "link_source_role_webview_overlay":
                for rel in ["selected_link_source_role_native_webview2_launch.log", "r42cr_native_editor_server/r42cr_server_ready.json"]:
                    add(zf, base / rel, "_runtime/" + str((base / rel).relative_to(ROOT)).replace("\\", "/"), manifest)
                continue
            for d in latest_dirs(base, 10):
                for p in d.rglob("*"):
                    if p.is_file() and p.suffix.lower() in EXTS and p.stat().st_size <= 5_000_000:
                        add(zf, p, "_runtime/" + str(p.relative_to(ROOT)).replace("\\", "/"), manifest)
        zf.writestr("r42dx_debug_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    downloads = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Downloads" / zip_path.name
    try:
        shutil.copy2(zip_path, downloads)
        print("[DONE] Created ZIP:", zip_path)
        print("[DONE] Copied ZIP to Downloads:", downloads)
        print("[DONE] Files included:", len(manifest))
    except Exception as exc:
        print("[DONE] Created ZIP:", zip_path)
        print("[WARN] Could not copy to Downloads:", repr(exc))
        print("[DONE] Files included:", len(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
