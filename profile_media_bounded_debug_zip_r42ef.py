#!/usr/bin/env python3
"""
R42EF bounded debug ZIP helper.

Purpose:
- Do not re-run archive/network/app/WebView2 probes.
- Do not dump giant audit_rows JSON to console.
- Do not recursively scan all profile_media_live_captures.
- Avoid Windows junction/reparse recursion.
- Use allowZip64=True, but also skip oversized files so upload ZIPs stay small.
"""
from __future__ import annotations

import csv
import json
import os
import shutil
import sys
import time
import zipfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, Iterator, Optional

VERSION = "20260907_r42ef_bounded_debug_zip64_hotfix"
SCHEMA = "ytce.r42ef.bounded_debug_zip64_hotfix.v1"

DEFAULT_MAX_FILE_BYTES = 16 * 1024 * 1024
DEFAULT_MAX_TOTAL_BYTES = 96 * 1024 * 1024
DEFAULT_MAX_FILES = 250

SKIP_DIR_NAMES = {
    ".git", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".venv", "venv", "env", "bin", "obj", "dist", "build", "Cache", "cache", "tmp", "temp",
}
SKIP_SUFFIXES = {
    ".mp4", ".mov", ".mkv", ".avi", ".webm", ".wav", ".mp3", ".m4a", ".flac",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff",
    ".dll", ".exe", ".pdb", ".bin", ".zip", ".7z", ".tar", ".gz", ".xz",
    ".sqlite", ".sqlite3", ".db", ".wal", ".shm",
}
ALWAYS_KEEP_NAMES = {
    "r42ed_semantic_media_logic_adapter_matrix.json",
    "r42ed_semantic_media_logic_adapter_matrix.md",
    "r42ed_payload_row_comprehension_audit.csv",
    "r42ed_adapter_guard_matrix.csv",
    "r42ed_text_colour_cleanup_css.txt",
    "r42ee_bounded_payload_scan_hotfix_no_gui_summary.json",
    "r42ec_archive_role_closeout_no_gui_summary.json",
    "archive_role_overlay_payload_r42dw_summary.json",
}
ROOT_SOURCE_FILES = [
    "profile_media_semantic_media_logic_matrix_r42ed.py",
    "profile_media_semantic_media_logic_matrix_r42ed_test.py",
    "profile_media_semantic_media_logic_matrix_r42ee_test.py",
    "profile_media_archive_role_payload_r42dw.py",
    "profile_media_archive_role_local_fixture_r42eb.py",
    "profile_media_archive_role_closeout_r42ec.py",
    "R42ED_SEMANTIC_MEDIA_LOGIC_ADAPTER_MATRIX_NOTES_20260907.md",
    "R42EE_BOUNDED_PAYLOAD_SCAN_HOTFIX_NOTES_20260907.md",
]
TOOL_FILES = [
    "tools/webview2_source_role_editor_native/_r42ee_python.cmd",
    "tools/webview2_source_role_editor_native/_r42ef_python.cmd",
    "tools/webview2_source_role_editor_native/smoke_r42ee_bounded_payload_scan_hotfix.cmd",
    "tools/webview2_source_role_editor_native/probe_r42ee_bounded_payload_scan_hotfix_no_gui.cmd",
    "tools/webview2_source_role_editor_native/probe_r42ee_bounded_payload_scan_hotfix_no_gui_recolor.cmd",
    "tools/webview2_source_role_editor_native/probe_r42ee_bounded_payload_scan_hotfix_no_gui.py",
    "tools/webview2_source_role_editor_native/make_r42ee_bounded_payload_scan_hotfix_debug_upload_zip.cmd",
    "tools/webview2_source_role_editor_native/make_r42ee_bounded_payload_scan_hotfix_debug_upload_zip.py",
    "tools/webview2_source_role_editor_native/make_r42ef_bounded_debug_upload_zip.cmd",
    "tools/webview2_source_role_editor_native/make_r42ef_bounded_debug_upload_zip.py",
]

@dataclass
class ZipSummary:
    schema: str
    version: str
    created_at_local: str
    mode: str
    root: str
    zip_path: str
    downloads_zip_path: str
    included_files: int
    included_bytes: int
    skipped_files: int
    skipped_reasons: dict
    selected_output_dirs: list[str]
    source_files_included: int
    side_effects: dict
    verdict: dict


def now_stamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def local_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def project_root_from_here() -> Path:
    here = Path(__file__).resolve()
    for p in [Path.cwd().resolve(), here.parent, *here.parents]:
        if (p / "main.py").exists() or (p / "tools" / "webview2_source_role_editor_native").exists():
            return p
    return Path.cwd().resolve()


def is_reparse_or_symlink(path: Path) -> bool:
    try:
        return path.is_symlink() or bool(os.stat(path, follow_symlinks=False).st_file_attributes & getattr(__import__('stat'), 'FILE_ATTRIBUTE_REPARSE_POINT', 0))
    except Exception:
        return path.is_symlink()


def safe_iter_files(base: Path, *, max_depth: int = 5) -> Iterator[Path]:
    base = base.resolve()
    stack: list[tuple[Path, int]] = [(base, 0)]
    while stack:
        current, depth = stack.pop()
        if depth > max_depth:
            continue
        try:
            entries = list(os.scandir(current))
        except OSError:
            continue
        for ent in entries:
            name = ent.name
            path = Path(ent.path)
            try:
                if ent.is_dir(follow_symlinks=False):
                    if name in SKIP_DIR_NAMES or path.is_symlink():
                        continue
                    stack.append((path, depth + 1))
                elif ent.is_file(follow_symlinks=False):
                    yield path
            except OSError:
                continue


def latest_dirs(root: Path, rel: str, prefix: str, limit: int = 3) -> list[Path]:
    base = root / rel
    if not base.exists():
        return []
    out: list[Path] = []
    try:
        for ent in os.scandir(base):
            p = Path(ent.path)
            if ent.is_dir(follow_symlinks=False) and ent.name.startswith(prefix) and not p.is_symlink():
                out.append(p)
    except OSError:
        return []
    out.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    return out[:limit]


def candidate_output_dirs(root: Path) -> list[Path]:
    rels = [
        ("profile_media_live_captures/r42ee_bounded_payload_scan_hotfix", "matrix_"),
        ("profile_media_live_captures/r42ec_archive_role_closeout_no_gui", "probe_"),
        ("profile_media_live_captures/r42eb_archive_role_local_fixture", "probe_"),
        ("profile_media_live_captures/r42ed_semantic_media_logic_adapter_matrix", "matrix_"),
    ]
    seen: set[str] = set()
    out: list[Path] = []
    for rel, prefix in rels:
        for p in latest_dirs(root, rel, prefix, limit=2):
            k = str(p.resolve()).lower()
            if k not in seen:
                seen.add(k)
                out.append(p)
    return out


def should_include_file(path: Path, *, max_file_bytes: int) -> tuple[bool, str]:
    name = path.name
    suffix = path.suffix.lower()
    try:
        size = path.stat().st_size
    except OSError:
        return False, "stat_failed"
    if size > max_file_bytes:
        return False, "over_max_file_bytes"
    if name in ALWAYS_KEEP_NAMES:
        return True, "always_keep"
    if suffix in SKIP_SUFFIXES:
        return False, "binary_or_heavy_suffix"
    # Keep debug evidence / source / manifests; skip large raw HTML unless explicitly tiny.
    if suffix in {".json", ".jsonl", ".md", ".txt", ".csv", ".py", ".cmd", ".cs", ".csproj", ".log"}:
        if suffix == ".log" and size > 2_000_000:
            return False, "large_log"
        return True, "text_debug"
    return False, "not_debug_file_type"


def arcname_for(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except Exception:
        return path.name


def add_file(zf: zipfile.ZipFile, root: Path, path: Path, included: list[tuple[str, int]], skipped: list[tuple[str, str, int]], *, max_file_bytes: int, max_total_bytes: int) -> int:
    ok, reason = should_include_file(path, max_file_bytes=max_file_bytes)
    try:
        size = path.stat().st_size
    except OSError:
        size = 0
    rel = arcname_for(root, path)
    if not ok:
        skipped.append((rel, reason, size))
        return 0
    current_total = sum(v for _, v in included)
    if current_total + size > max_total_bytes:
        skipped.append((rel, "over_max_total_bytes", size))
        return 0
    zf.write(path, rel)
    included.append((rel, size))
    return 1


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def build_bounded_debug_zip(
    root: Optional[Path] = None,
    *,
    label: str = "r42ef_bounded_debug_zip64_hotfix",
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
    max_files: int = DEFAULT_MAX_FILES,
    print_json: bool = True,
) -> ZipSummary:
    root = (root or project_root_from_here()).resolve()
    stamp = now_stamp()
    outbase = root / "profile_media_live_captures" / "r42ef_bounded_debug_zip64_hotfix"
    outdir = outbase / f"zipbuild_{stamp}"
    outdir.mkdir(parents=True, exist_ok=True)
    zip_path = outbase / f"{label}_{stamp}.zip"
    downloads = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Downloads" / zip_path.name

    output_dirs = candidate_output_dirs(root)
    included: list[tuple[str, int]] = []
    skipped: list[tuple[str, str, int]] = []
    source_files_included = 0

    staging_manifest = outdir / "r42ef_zip_selection_manifest.csv"
    with staging_manifest.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["action", "path", "reason", "size"])
        for p in [*(root / rel for rel in ROOT_SOURCE_FILES), *(root / rel for rel in TOOL_FILES)]:
            if p.exists() and p.is_file():
                try:
                    writer.writerow(["candidate_source", arcname_for(root, p), "explicit", p.stat().st_size])
                except OSError:
                    pass
        for d in output_dirs:
            writer.writerow(["candidate_dir", arcname_for(root, d), "latest_bounded", ""])

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
        # First include this helper's own compact selection manifest.
        add_file(zf, root, staging_manifest, included, skipped, max_file_bytes=max_file_bytes, max_total_bytes=max_total_bytes)
        for rel in ROOT_SOURCE_FILES:
            p = root / rel
            if p.exists() and p.is_file():
                before = len(included)
                add_file(zf, root, p, included, skipped, max_file_bytes=max_file_bytes, max_total_bytes=max_total_bytes)
                if len(included) > before:
                    source_files_included += 1
        for rel in TOOL_FILES:
            p = root / rel
            if p.exists() and p.is_file():
                add_file(zf, root, p, included, skipped, max_file_bytes=max_file_bytes, max_total_bytes=max_total_bytes)
        for d in output_dirs:
            for p in safe_iter_files(d, max_depth=4):
                if len(included) >= max_files:
                    skipped.append((arcname_for(root, p), "over_max_files", p.stat().st_size if p.exists() else 0))
                    continue
                add_file(zf, root, p, included, skipped, max_file_bytes=max_file_bytes, max_total_bytes=max_total_bytes)

        # Add compact summary inside the ZIP after current selection is known.
        skip_reasons: dict[str, int] = {}
        for _, reason, _ in skipped:
            skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
        summary_data = {
            "schema": SCHEMA,
            "version": VERSION,
            "created_at_local": local_iso(),
            "mode": "NO_GUI_NO_NETWORK_NO_ARCHIVE_HIT_COMPACT_ZIP_BUILD",
            "root": str(root),
            "zip_path": str(zip_path),
            "downloads_zip_path": str(downloads),
            "included_files": len(included),
            "included_bytes": sum(v for _, v in included),
            "skipped_files": len(skipped),
            "skipped_reasons": skip_reasons,
            "selected_output_dirs": [str(p) for p in output_dirs],
            "source_files_included": source_files_included,
            "side_effects": {
                "archive_ph_hit": False,
                "network_actions_performed": False,
                "native_webview2_started": False,
                "app_started": False,
                "tor_camoufox_started": False,
                "openclaw_tool_call_performed": False,
                "credentials_read": False,
            },
            "verdict": {
                "zip64_enabled": True,
                "bounded_dirs_only": True,
                "unbounded_profile_media_live_captures_scan": False,
                "console_audit_rows_dump_suppressed": True,
                "ready_for_upload": True,
            },
        }
        tmp_summary = outdir / "r42ef_bounded_debug_zip64_hotfix_summary.json"
        write_json(tmp_summary, summary_data)
        zf.write(tmp_summary, arcname_for(root, tmp_summary))

    downloads.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(zip_path, downloads)

    # Recompute final summary including the summary file itself.
    final_reasons: dict[str, int] = {}
    for _, reason, _ in skipped:
        final_reasons[reason] = final_reasons.get(reason, 0) + 1
    summary = ZipSummary(
        schema=SCHEMA,
        version=VERSION,
        created_at_local=local_iso(),
        mode="NO_GUI_NO_NETWORK_NO_ARCHIVE_HIT_COMPACT_ZIP_BUILD",
        root=str(root),
        zip_path=str(zip_path),
        downloads_zip_path=str(downloads),
        included_files=len(included) + 1,
        included_bytes=sum(v for _, v in included) + (outdir / "r42ef_bounded_debug_zip64_hotfix_summary.json").stat().st_size,
        skipped_files=len(skipped),
        skipped_reasons=final_reasons,
        selected_output_dirs=[str(p) for p in output_dirs],
        source_files_included=source_files_included,
        side_effects={
            "archive_ph_hit": False,
            "network_actions_performed": False,
            "native_webview2_started": False,
            "app_started": False,
            "tor_camoufox_started": False,
            "openclaw_tool_call_performed": False,
            "credentials_read": False,
        },
        verdict={
            "zip_created": zip_path.exists(),
            "copied_to_downloads": downloads.exists(),
            "zip64_enabled": True,
            "bounded_dirs_only": True,
            "unbounded_profile_media_live_captures_scan": False,
            "console_audit_rows_dump_suppressed": True,
            "ready_for_upload": zip_path.exists() and downloads.exists(),
        },
    )
    write_json(outdir / "r42ef_bounded_debug_zip64_hotfix_summary.json", asdict(summary))
    if print_json:
        print(json.dumps(asdict(summary), indent=2, ensure_ascii=False))
        print(f"[DONE] Created ZIP: {zip_path}")
        print(f"[DONE] Copied ZIP to Downloads: {downloads}")
        print(f"[DONE] Files included: {summary.included_files}")
    return summary


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    root = Path(argv[0]).resolve() if argv else project_root_from_here()
    summary = build_bounded_debug_zip(root=root, print_json=True)
    return 0 if summary.verdict.get("ready_for_upload") else 2


if __name__ == "__main__":
    raise SystemExit(main())
