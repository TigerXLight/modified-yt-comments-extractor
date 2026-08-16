from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from profile_media_profile_intake import (
    PROFILE_MEDIA_PROFILE_INTAKE_CONFIRMATION,
    apply_profile_intake_plan,
    build_profile_intake_plan,
    result_payload,
)


def _read_profile_text(args: argparse.Namespace) -> str:
    if args.profile_text_file:
        return Path(args.profile_text_file).read_text(encoding="utf-8")
    return args.profile_text or ""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan or write guarded Profile/Media profile records (V75S).")
    parser.add_argument("--database-root", required=True)
    parser.add_argument("--case-title", required=True)
    parser.add_argument("--case-root", default="")
    parser.add_argument("--canonical-name", default="")
    parser.add_argument("--profile-text", default="")
    parser.add_argument("--profile-text-file", default="")
    parser.add_argument("--source-bucket", default="Articles")
    parser.add_argument("--source-role", default="UNKNOWN_SOURCE_ROLE")
    parser.add_argument("--claim-basis", default="UNKNOWN_CLAIM_BASIS")
    parser.add_argument("--currentness-status", default="UNKNOWN")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm-write", default="")
    parser.add_argument("--print-plan", action="store_true")
    parser.add_argument("--print-confirmation", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.print_confirmation:
        print(PROFILE_MEDIA_PROFILE_INTAKE_CONFIRMATION)
        return 0
    plan = build_profile_intake_plan(
        database_root=args.database_root,
        case_title=args.case_title,
        case_root=args.case_root,
        canonical_name=args.canonical_name,
        profile_text=_read_profile_text(args),
        source_bucket=args.source_bucket,
        source_role=args.source_role,
        claim_basis=args.claim_basis,
        currentness_status=args.currentness_status,
        execute=args.execute,
        confirmation_phrase=args.confirm_write,
    )
    result = apply_profile_intake_plan(plan)
    payload = result_payload(result, plan=plan if args.print_plan else None)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.status not in {"blocked_confirmation_required", "blocked_path_outside_database_or_conflict"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
