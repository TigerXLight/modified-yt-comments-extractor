from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_database_end_to_end_workflow import (
    confirmation_phrases,
    build_end_to_end_config_from_files,
    end_to_end_workflow_payload,
    render_end_to_end_workflow_text,
    run_profile_media_database_end_to_end_workflow,
)
from profile_media_database_implementation_closeout import (
    build_implementation_closeout_report,
    implementation_closeout_payload,
    render_implementation_closeout_text,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="V76H end-to-end Profile/Media Database workflow proof")
    parser.add_argument("--tree-list", action="append", default=[], help="Explicit text file of folder-tree paths; no filesystem scan is performed.")
    parser.add_argument("--database-root", default="", help="Database root for materialization/folder operation review.")
    parser.add_argument("--case-title", default="", help="Optional case title override.")
    parser.add_argument("--batch-preview-path", default="", help="Standalone preview batch JSON path.")
    parser.add_argument("--write-preview", action="store_true", help="Write preview JSON only when the exact write confirmation is supplied.")
    parser.add_argument("--confirm-write", default="", help="Must equal WRITE_EXISTING_FOLDER_BATCH_PREVIEW.")
    parser.add_argument("--materialize", action="store_true", help="Create folders/metadata only when materialize confirmation is supplied.")
    parser.add_argument("--confirm-materialize", default="", help="Must equal MATERIALIZE_PROFILE_MEDIA_DATABASE_SELECTION.")
    parser.add_argument("--folder-operations-json", default="", help="Explicit reviewed folder operations JSON file.")
    parser.add_argument("--execute-folder-operations", action="store_true", help="Apply reviewed folder operations only when confirmation is supplied.")
    parser.add_argument("--confirm-folder-operations", default="", help="Must equal APPLY_PROFILE_MEDIA_REVIEWED_FOLDER_OPERATIONS.")
    parser.add_argument("--print-workflow-text", action="store_true")
    parser.add_argument("--print-closeout", action="store_true")
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--show-confirmation-phrases", action="store_true")
    parser.add_argument("--reset-demo-root", action="store_true", help="Delete database root first; intended for disposable temp demos only.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.show_confirmation_phrases:
        print(json.dumps({"schema_version": "profile-media-database-end-to-end-cli-v76h", "confirmation_phrases": confirmation_phrases()}, indent=2, sort_keys=True))
        return 0
    if args.reset_demo_root and args.database_root:
        root = Path(args.database_root)
        # The flag name explicitly scopes this to disposable demo roots.  Still
        # refuse obvious high-level paths.
        text = str(root).replace("\\", "/").lower()
        if len(str(root)) > 10 and ("temp" in text or "tmp" in text or "demo" in text):
            shutil.rmtree(root, ignore_errors=True)
    config = build_end_to_end_config_from_files(
        tree_list_paths=args.tree_list,
        database_root=args.database_root,
        case_title=args.case_title,
        batch_preview_path=args.batch_preview_path,
        write_batch_preview=args.write_preview,
        batch_write_confirmation=args.confirm_write,
        materialize_database=args.materialize,
        materialize_confirmation=args.confirm_materialize,
        operations_json_path=args.folder_operations_json,
        execute_folder_operations=args.execute_folder_operations,
        folder_operations_confirmation=args.confirm_folder_operations,
    )
    result = run_profile_media_database_end_to_end_workflow(config)
    closeout = build_implementation_closeout_report(result)
    payload = end_to_end_workflow_payload(result, include_text=not args.compact or args.print_workflow_text)
    if args.print_workflow_text:
        payload["workflow_text"] = render_end_to_end_workflow_text(result)
    if args.print_closeout:
        payload["implementation_closeout"] = implementation_closeout_payload(closeout, include_text=not args.compact)
        if not args.compact:
            payload["implementation_closeout_text"] = render_implementation_closeout_text(closeout)
    print(json.dumps(payload, indent=None if args.compact else 2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
