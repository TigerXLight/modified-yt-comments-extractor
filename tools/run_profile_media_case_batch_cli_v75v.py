from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_case_batch import (  # noqa: E402
    PROFILE_MEDIA_CASE_BATCH_CONFIRMATION,
    apply_case_batch_plan,
    build_case_batch_plan,
    load_case_batch_json,
    result_payload,
    write_demo_case_batch_json,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan or explicitly apply a Profile/Media case batch JSON.")
    parser.add_argument("--batch-json", default="", help="Path to a case batch JSON file.")
    parser.add_argument("--write-demo-batch", default="", help="Write a demo batch JSON file to this path and exit unless --batch-json is also supplied.")
    parser.add_argument("--database-root", default="", help="Override or provide the Database root.")
    parser.add_argument("--case-title", default="", help="Override or provide the case title.")
    parser.add_argument("--case-root", default="", help="Optional explicit case root inside the Database root.")
    parser.add_argument("--execute", action="store_true", help="Apply the batch, only with the exact confirmation phrase.")
    parser.add_argument("--confirm-batch", default="", help=f"Must equal {PROFILE_MEDIA_CASE_BATCH_CONFIRMATION} when --execute is used.")
    parser.add_argument("--print-plan", action="store_true", help="Include the human-readable plan text in JSON output.")
    args = parser.parse_args()

    if args.write_demo_batch:
        written = write_demo_case_batch_json(args.write_demo_batch, database_root=args.database_root, case_title=args.case_title or "Example Case")
        if not args.batch_json:
            print(json.dumps({"status": "demo_batch_written", "batch_json": written}, indent=2, sort_keys=True))
            return 0

    if not args.batch_json:
        parser.error("--batch-json is required unless only --write-demo-batch is requested")

    payload = load_case_batch_json(args.batch_json)
    plan = build_case_batch_plan(
        payload=payload,
        database_root=args.database_root,
        case_title=args.case_title,
        case_root=args.case_root,
        execute=args.execute,
        confirmation_phrase=args.confirm_batch,
    )
    result = apply_case_batch_plan(plan)
    output = result_payload(result, plan=plan if args.print_plan else None)
    print(json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if not result.status.startswith("blocked") else 2


if __name__ == "__main__":
    raise SystemExit(main())
