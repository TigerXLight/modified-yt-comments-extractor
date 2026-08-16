from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_existing_folder_batch_planner import (
    PROFILE_MEDIA_EXISTING_FOLDER_BATCH_WRITE_CONFIRMATION,
    build_existing_folder_to_batch_plan,
    load_folder_tree_lines,
    render_existing_folder_plan_text,
    write_batch_preview_if_confirmed,
)
from profile_media_existing_folder_gui_adapter import build_existing_folder_gui_payload
from profile_media_source_role_policy import build_source_role_policy_report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="V76E dry-run existing folder to Profile/Media batch planner")
    parser.add_argument("--tree-list", action="append", default=[], help="Explicit text file containing folder-tree paths; this is not a folder scan.")
    parser.add_argument("--database-root", default="", help="Display database root for the preview.")
    parser.add_argument("--case-title", default="", help="Optional case title override for direct case-folder listings.")
    parser.add_argument("--write-preview", default="", help="Optional output JSON path for guarded standalone batch preview.")
    parser.add_argument("--confirm-write", default="", help="Must equal WRITE_EXISTING_FOLDER_BATCH_PREVIEW to write preview JSON.")
    parser.add_argument("--print-plan", action="store_true")
    parser.add_argument("--print-batch-preview", action="store_true")
    parser.add_argument("--print-gui-payload", action="store_true")
    parser.add_argument("--role-policy-report", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    lines: list[str] = []
    for tree_path in args.tree_list:
        lines.extend(load_folder_tree_lines(tree_path))
    plan = build_existing_folder_to_batch_plan(lines, database_root=args.database_root, case_title=args.case_title)
    payload = plan.to_dict()
    result: dict[str, object] = {
        "schema_version": "profile-media-existing-folder-cli-v76e",
        "status": "dry_run_preview",
        "plan": payload,
        "folder_scan_performed": False,
        "folder_creation_performed": False,
        "folder_move_performed": False,
        "folder_rename_performed": False,
        "file_copy_performed": False,
        "media_download_performed": False,
        "automatic_classification_performed": False,
        "sensitive_identifier_inference_performed": False,
    }
    if args.write_preview:
        write_result = write_batch_preview_if_confirmed(plan, args.write_preview, confirmation_phrase=args.confirm_write)
        result["write_result"] = write_result.to_dict()
        result["file_write_performed"] = write_result.file_write_performed
    else:
        result["file_write_performed"] = False
    if args.role_policy_report:
        roles = [candidate.source_role for candidate in plan.source_candidates] + [candidate.source_role for candidate in plan.profile_candidates]
        result["role_policy_report"] = build_source_role_policy_report(roles).to_dict()
    if args.print_plan:
        result["plan_text"] = render_existing_folder_plan_text(plan)
    if args.print_batch_preview:
        result["batch_preview"] = plan.batch_preview()
    if args.print_gui_payload:
        result["gui_payload"] = build_existing_folder_gui_payload(plan).to_dict()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
