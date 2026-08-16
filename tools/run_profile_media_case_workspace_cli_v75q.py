from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_case_workspace import (
    PROFILE_MEDIA_CASE_WORKSPACE_CONFIRMATION,
    apply_case_workspace_plan,
    build_case_workspace_plan,
    result_payload,
    write_case_workspace_plan_json,
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plan or explicitly create the Profile/Media Database case folder skeleton. Default is dry-run."
    )
    parser.add_argument("--database-root", required=True, help="Database root, for example T:\\Database")
    parser.add_argument("--case-title", required=True, help="Case folder title to plan/create.")
    parser.add_argument("--case-root", default="", help="Optional exact case root. Defaults to database-root\\Cases\\case-title.")
    parser.add_argument("--execute", action="store_true", help="Actually create the planned folders.")
    parser.add_argument(
        "--confirm-create",
        default="",
        help=f"Required with --execute. Must equal {PROFILE_MEDIA_CASE_WORKSPACE_CONFIRMATION}.",
    )
    parser.add_argument("--plan-out", default="", help="Optional path to write plan JSON.")
    parser.add_argument("--create-parent", action="store_true", help="Allow parent creation for --plan-out only.")
    parser.add_argument("--print-plan", action="store_true", help="Include human-readable plan text in JSON output.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    plan = build_case_workspace_plan(
        database_root=args.database_root,
        case_title=args.case_title,
        case_root=args.case_root,
        execute=args.execute,
        confirmation_phrase=args.confirm_create,
    )
    result = apply_case_workspace_plan(plan)
    payload = result_payload(result, plan=plan if args.print_plan else None)
    if args.plan_out:
        payload["plan_out"] = write_case_workspace_plan_json(plan, args.plan_out, create_parent=args.create_parent)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.status in {"planned_dry_run", "created", "already_exists"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
