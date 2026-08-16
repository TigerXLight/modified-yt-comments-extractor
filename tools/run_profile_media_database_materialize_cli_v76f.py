from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from profile_media_case_batch import build_demo_case_batch_payload
from profile_media_database_materialize_gui_adapter import build_materialize_gui_payload, materialize_gui_payload_dict
from profile_media_database_materialize_workflow import (
    PROFILE_MEDIA_DATABASE_MATERIALIZE_CONFIRMATION,
    apply_database_materialize_plan,
    build_database_materialize_plan,
    materialize_workflow_payload,
)


def _write_demo_batch(path: str, *, database_root: str, case_title: str) -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = build_demo_case_batch_payload(database_root=database_root, case_title=case_title)
    # Keep a legacy role in the demo so the V76E normalization policy is tested
    # through the V76F materialize path.
    payload["sources"][1]["source_role"] = "SECONDARY_WITNESS_SOURCE"
    payload["profiles"][1]["source_role"] = "SECONDARY_WITNESS_SOURCE"
    target.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return str(target)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the V76F controlled Profile/Media Database materialize workflow.")
    parser.add_argument("--batch-json", action="append", default=[], help="Explicit batch JSON file. May be repeated.")
    parser.add_argument("--write-demo-batch", default="", help="Write a demo batch JSON at this path before planning.")
    parser.add_argument("--database-root", required=True, help="Target database root for planning/execution.")
    parser.add_argument("--case-title", default="V76F Controlled Materialize Demo Case")
    parser.add_argument("--execute", action="store_true", help="Request real folder creation and metadata writes.")
    parser.add_argument("--confirmation", default="", help=f"Must equal {PROFILE_MEDIA_DATABASE_MATERIALIZE_CONFIRMATION} for execution.")
    parser.add_argument("--print-plan", action="store_true")
    parser.add_argument("--print-gui-payload", action="store_true")
    args = parser.parse_args(argv)

    batch_files = list(args.batch_json)
    if args.write_demo_batch:
        batch_files.append(_write_demo_batch(args.write_demo_batch, database_root=args.database_root, case_title=args.case_title))

    plan = build_database_materialize_plan(
        database_root=args.database_root,
        batch_json_files=batch_files,
        execute=args.execute,
        confirmation_phrase=args.confirmation,
    )
    result = apply_database_materialize_plan(plan)
    payload = materialize_workflow_payload(result, plan=plan)
    if args.print_gui_payload:
        payload["gui_payload"] = materialize_gui_payload_dict(build_materialize_gui_payload(plan, result))
    elif args.print_plan:
        payload["gui_payload"] = materialize_gui_payload_dict(build_materialize_gui_payload(plan))
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.status in {"planned_dry_run", "materialized"} else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
