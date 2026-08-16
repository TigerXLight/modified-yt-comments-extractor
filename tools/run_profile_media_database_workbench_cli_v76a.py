from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_case_batch import write_demo_case_batch_json  # noqa: E402
from profile_media_database_session import ProfileMediaDatabaseSessionConfig  # noqa: E402
from profile_media_database_workbench import (  # noqa: E402
    PROFILE_MEDIA_DATABASE_WORKBENCH_EXPORT_CONFIRMATION,
    apply_workbench_export_plan,
    build_workbench_export_plan,
    build_workbench_state,
    workbench_payload,
)


def _tri_state(value: str) -> bool | None:
    normalized = (value or "any").strip().lower()
    if normalized in {"any", "", "none", "null"}:
        return None
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError("expected any, true, or false")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a full Profile/Media Database workbench snapshot from explicit batch JSON files."
    )
    parser.add_argument("--batch-json", action="append", default=[], help="Explicit case batch JSON file. May be repeated.")
    parser.add_argument("--write-demo-batch", default="", help="Write a demo batch JSON file to this path and use it when no --batch-json is supplied.")
    parser.add_argument("--database-root", default="", help="Database root label/path used for the workbench state.")
    parser.add_argument("--case-title", default="Example Case", help="Case title used when writing a demo batch.")
    parser.add_argument("--profile-name", default="", help="Profile name contains filter.")
    parser.add_argument("--case-title-filter", default="", help="Case title contains filter.")
    parser.add_argument("--source-bucket", default="", help="Source bucket contains filter.")
    parser.add_argument("--source-role", default="", help="Source role contains filter.")
    parser.add_argument("--claim-basis", default="", help="Claim basis contains filter.")
    parser.add_argument("--currentness-status", default="", help="Currentness status contains filter.")
    parser.add_argument("--text", default="", help="General text contains filter.")
    parser.add_argument("--source-chain-gap", type=_tri_state, default=None, help="any, true, or false. Default: any.")
    parser.add_argument("--disputed-framing", type=_tri_state, default=None, help="any, true, or false. Default: any.")
    parser.add_argument("--has-parser-warnings", type=_tri_state, default=None, help="any, true, or false. Default: any.")
    parser.add_argument("--limit", type=int, default=0, help="Maximum matched source/profile rows. 0 means all.")
    parser.add_argument("--print-workbench", action="store_true", help="Include human-readable workbench text.")
    parser.add_argument("--export-dir", default="", help="Plan or write workbench export files to this directory.")
    parser.add_argument("--execute-export", action="store_true", help="Actually write export files; requires --confirm-export.")
    parser.add_argument("--confirm-export", default="", help=f"Exact confirmation phrase: {PROFILE_MEDIA_DATABASE_WORKBENCH_EXPORT_CONFIRMATION}")
    args = parser.parse_args()

    batch_paths = list(args.batch_json)
    if args.write_demo_batch:
        written = write_demo_case_batch_json(args.write_demo_batch, database_root=args.database_root, case_title=args.case_title)
        if not batch_paths:
            batch_paths.append(written)
    config = ProfileMediaDatabaseSessionConfig(
        database_root=args.database_root,
        batch_json_files=tuple(batch_paths),
        mode="DATABASE",
        profile_name=args.profile_name,
        case_title=args.case_title_filter,
        source_bucket=args.source_bucket,
        source_role=args.source_role,
        claim_basis=args.claim_basis,
        currentness_status=args.currentness_status,
        text=args.text,
        source_chain_gap=args.source_chain_gap,
        disputed_framing=args.disputed_framing,
        has_parser_warnings=args.has_parser_warnings,
        limit=max(0, int(args.limit or 0)),
    )
    workbench = build_workbench_state(config)
    export_plan = None
    export_result = None
    if args.export_dir:
        export_plan = build_workbench_export_plan(
            args.export_dir,
            execute=args.execute_export,
            confirmation_phrase=args.confirm_export,
        )
        export_result = apply_workbench_export_plan(export_plan, workbench)
    output = workbench_payload(
        workbench,
        include_text=args.print_workbench,
        export_plan=export_plan,
        export_result=export_result,
    )
    print(json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if not (export_result and export_result.status.startswith("blocked")) else 2


if __name__ == "__main__":
    raise SystemExit(main())
