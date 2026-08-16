from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_case_batch import write_demo_case_batch_json  # noqa: E402
from profile_media_database_session import (  # noqa: E402
    PROFILE_MEDIA_DATABASE_EXPORT_CONFIRMATION,
    ProfileMediaDatabaseSessionConfig,
    apply_database_export_plan,
    build_database_export_plan,
    build_database_session_snapshot,
    database_session_config_from_mapping,
    load_database_session_config,
    render_database_session_text,
    write_database_session_config,
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
        description="Build a Profile/Media Database session snapshot from explicit case batch JSON files and optionally export it."
    )
    parser.add_argument("--session-config", default="", help="Optional explicit session config JSON file.")
    parser.add_argument("--write-session-config", default="", help="Write the resolved session config JSON to this path.")
    parser.add_argument("--batch-json", action="append", default=[], help="Explicit case batch JSON file. May be repeated.")
    parser.add_argument("--write-demo-batch", default="", help="Write a demo batch JSON file to this path and use it when no --batch-json is provided.")
    parser.add_argument("--database-root", default="", help="Database root used for demo/config/session state.")
    parser.add_argument("--case-title", default="Example Case", help="Case title used when writing a demo batch.")
    parser.add_argument("--mode", choices=("FILES", "DATABASE"), default="DATABASE", help="Mode for the session snapshot.")
    parser.add_argument("--profile-name", default="", help="Profile name contains filter.")
    parser.add_argument("--case-title-filter", default="", help="Case title contains filter for searching.")
    parser.add_argument("--source-bucket", default="", help="Source bucket contains filter, e.g. Articles or Social Media/Online.")
    parser.add_argument("--source-role", default="", help="Source role contains filter.")
    parser.add_argument("--claim-basis", default="", help="Claim basis contains filter.")
    parser.add_argument("--currentness-status", default="", help="Currentness status contains filter.")
    parser.add_argument("--text", default="", help="General text contains filter across indexed row fields.")
    parser.add_argument("--source-chain-gap", type=_tri_state, default=None, help="any, true, or false. Default: any.")
    parser.add_argument("--disputed-framing", type=_tri_state, default=None, help="any, true, or false. Default: any.")
    parser.add_argument("--has-parser-warnings", type=_tri_state, default=None, help="any, true, or false. Default: any.")
    parser.add_argument("--limit", type=int, default=0, help="Maximum matched source rows and profile rows to return. 0 means all.")
    parser.add_argument("--print-session", action="store_true", help="Include a human-readable session text block.")
    parser.add_argument("--export-dir", default="", help="Plan or write Database mode export files to this directory.")
    parser.add_argument("--execute-export", action="store_true", help="Actually write export files; requires --confirm-export.")
    parser.add_argument("--confirm-export", default="", help=f"Exact confirmation phrase: {PROFILE_MEDIA_DATABASE_EXPORT_CONFIRMATION}")
    args = parser.parse_args()

    if args.session_config:
        config = load_database_session_config(args.session_config)
    else:
        batch_paths = list(args.batch_json)
        if args.write_demo_batch:
            written = write_demo_case_batch_json(args.write_demo_batch, database_root=args.database_root, case_title=args.case_title)
            if not batch_paths:
                batch_paths.append(written)
        config = ProfileMediaDatabaseSessionConfig(
            database_root=args.database_root,
            batch_json_files=tuple(batch_paths),
            mode=args.mode,
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

    if args.write_session_config:
        write_database_session_config(args.write_session_config, config)

    snapshot = build_database_session_snapshot(config)
    output = snapshot.to_dict(include_view_text=args.print_session)
    if args.print_session:
        output["session_text"] = render_database_session_text(snapshot)
    if args.export_dir:
        plan = build_database_export_plan(
            args.export_dir,
            execute=args.execute_export,
            confirmation_phrase=args.confirm_export,
        )
        result = apply_database_export_plan(plan, snapshot)
        output["export_plan"] = plan.to_dict()
        output["export_result"] = result.to_dict()
    print(json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
