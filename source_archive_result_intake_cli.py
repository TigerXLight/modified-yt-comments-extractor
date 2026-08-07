from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from source_archive_result_intake import build_source_archive_result_intake, dump_json, load_json_file
from source_archive_result_intake_store import store_source_archive_result_intake


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build shared archive result intake from operator-supplied archive results.")
    parser.add_argument("--archive-handoff-json", required=True, help="Path to source archive handoff package JSON.")
    parser.add_argument("--provider-tasks-json", help="Optional path to source archive provider tasks JSON.")
    parser.add_argument("--result-templates-json", help="Optional path to source archive result templates JSON.")
    parser.add_argument("--result-intake-handoff-json", help="Optional path to source archive result intake handoff JSON.")
    parser.add_argument("--archive-result-json", action="append", required=True, help="Operator-supplied archive result JSON; may be repeated.")
    parser.add_argument("--operator-id", default="manual_archive_operator", help="Non-secret archive operator identifier.")
    parser.add_argument("--intake-note", action="append", default=[], help="Optional intake note; may be repeated.")
    parser.add_argument("--output-dir", required=True, help="Directory where output JSON files will be written.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    outputs = build_source_archive_result_intake(
        archive_handoff_package=load_json_file(args.archive_handoff_json),
        provider_tasks=load_json_file(args.provider_tasks_json) if args.provider_tasks_json else None,
        result_templates=load_json_file(args.result_templates_json) if args.result_templates_json else None,
        result_intake_handoff=load_json_file(args.result_intake_handoff_json) if args.result_intake_handoff_json else None,
        operator_archive_results=[load_json_file(path) for path in args.archive_result_json],
        operator_id=args.operator_id,
        intake_notes=args.intake_note,
    )
    receipt = store_source_archive_result_intake(outputs.as_dict(), Path(args.output_dir))
    print(dump_json(receipt), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
