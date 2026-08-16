from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "project-capabilities-audit-cli-v76m"
REQUIRED_DOCS = (
    "PROJECT_CURRENT_CAPABILITIES_AND_FUNCTIONS_V76M.md",
    "PROJECT_FUNCTION_INDEX_V76M.md",
    "PROJECT_SCREENSHOT_ARCHIVE_CAPABILITIES_V76M.md",
    "PROFILE_MEDIA_DATABASE_CURRENT_CAPABILITIES_V76M.md",
    "PROJECT_CAPABILITY_GAPS_AND_NEXT_STEPS_V76M.md",
)
EXTERNAL_REFERENCE_FOLDER = "external_reference_sources_20260816_article_extraction"
KEY_MODULES = (
    "youtube_gui_media_queue.py",
    "jdownloader_internal_cnl.py",
    "source_media_execution_bridge.py",
    "asr_tools.py",
    "online_asr_execution_gate.py",
    "source_local_browser_execution.py",
    "source_replay_static_snapshot.py",
    "msn_source_adapter.py",
    "twitter_browser_capture_runner.py",
    "twitter_timeline_cursor_scheduler.py",
    "profile_media_article_extraction_adapter.py",
    "profile_media_database_end_to_end_workflow.py",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _git_ls_files(paths: list[str]) -> list[str]:
    root = _repo_root()
    try:
        completed = subprocess.run(
            ["git", "ls-files", *paths],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError:
        return []
    if completed.returncode != 0:
        return []
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def build_audit_payload() -> dict[str, Any]:
    root = _repo_root()
    docs = {name: (root / name).is_file() for name in REQUIRED_DOCS}
    modules = {name: (root / name).is_file() for name in KEY_MODULES}
    external_reference_path = root / EXTERNAL_REFERENCE_FOLDER
    external_tracked = bool(_git_ls_files([EXTERNAL_REFERENCE_FOLDER]))
    return {
        "schema_version": SCHEMA_VERSION,
        "repo_root": str(root),
        "repo_source_inventory_scan": True,
        "folder_scan_performed": False,
        "media_download_performed": False,
        "web_download_performed": False,
        "automatic_classification_performed": False,
        "sensitive_identifier_inference_performed": False,
        "user_media_database_home_scanned": False,
        "external_reference_folder": EXTERNAL_REFERENCE_FOLDER,
        "external_reference_folder_present": external_reference_path.exists(),
        "external_reference_folder_tracked": external_tracked,
        "required_docs": docs,
        "key_modules": modules,
        "summary": {
            "required_doc_count": len(REQUIRED_DOCS),
            "required_docs_present": sum(1 for present in docs.values() if present),
            "key_module_count": len(KEY_MODULES),
            "key_modules_present": sum(1 for present in modules.values() if present),
        },
    }


def render_text(payload: dict[str, Any]) -> str:
    lines = [
        "Project Capabilities Audit V76M",
        f"Schema: {payload['schema_version']}",
        f"Repo source inventory scan: {payload['repo_source_inventory_scan']}",
        f"Folder scan performed: {payload['folder_scan_performed']}",
        f"Media download performed: {payload['media_download_performed']}",
        f"Web download performed: {payload['web_download_performed']}",
        f"Automatic classification performed: {payload['automatic_classification_performed']}",
        f"Sensitive identifier inference performed: {payload['sensitive_identifier_inference_performed']}",
        f"External reference folder present: {payload['external_reference_folder_present']}",
        f"External reference folder tracked: {payload['external_reference_folder_tracked']}",
        f"Required docs present: {payload['summary']['required_docs_present']}/{payload['summary']['required_doc_count']}",
        f"Key modules present: {payload['summary']['key_modules_present']}/{payload['summary']['key_module_count']}",
        "",
        "Required docs:",
    ]
    for name, present in payload["required_docs"].items():
        lines.append(f"- {name}: {'present' if present else 'missing'}")
    lines.extend(["", "Key modules:"])
    for name, present in payload["key_modules"].items():
        lines.append(f"- {name}: {'present' if present else 'missing'}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only V76M project capabilities audit summary.")
    parser.add_argument("--print-text", action="store_true", help="Print a human-readable summary.")
    parser.add_argument("--json", action="store_true", help="Print JSON payload.")
    args = parser.parse_args(argv)
    payload = build_audit_payload()
    if args.print_text or not args.json:
        print(render_text(payload))
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

