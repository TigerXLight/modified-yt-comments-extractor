from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_database_operation_reconciliation import (
    PROFILE_MEDIA_DATABASE_RECONCILIATION_WRITE_CONFIRMATION,
    build_batch_reconciliation_plan,
    reconciliation_payload,
    render_batch_reconciliation_plan_text,
    write_reconciled_batch_preview_if_confirmed,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run V76I Profile/Media batch reconciliation from explicit JSON files.")
    parser.add_argument("--batch-json", required=True)
    parser.add_argument("--operations-json", required=True)
    parser.add_argument("--output-json", default="")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--confirm-write", default="")
    parser.add_argument("--print-plan", action="store_true")
    parser.add_argument("--print-payload", action="store_true")
    args = parser.parse_args(argv)

    plan = build_batch_reconciliation_plan(
        batch_json_path=args.batch_json,
        operations_json_path=args.operations_json,
        output_batch_json=args.output_json,
    )
    result = None
    if args.write:
        result = write_reconciled_batch_preview_if_confirmed(plan, confirmation_phrase=args.confirm_write)
    if args.print_plan:
        print(render_batch_reconciliation_plan_text(plan))
    payload = result.to_dict() if result else reconciliation_payload(plan)
    if args.print_payload or not args.print_plan:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    if args.write and result and result.status != "reconciled_batch_preview_written":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
