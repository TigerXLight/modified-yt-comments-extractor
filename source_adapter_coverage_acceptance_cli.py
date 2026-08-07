from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from source_adapter_coverage_acceptance import load_json
from source_adapter_coverage_acceptance_store import store_source_adapter_coverage_acceptance


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Accept local-only shared source adapter fixture coverage.")
    parser.add_argument("--fixture-pipeline-closeout-json", required=True, help="Source Adapter Fixture Pipeline Closeout package JSON.")
    parser.add_argument("--traceability-index-json", help="Optional Source Adapter Fixture Pipeline traceability index JSON.")
    parser.add_argument("--acceptance-handoff-json", help="Optional Source Adapter Fixture acceptance handoff JSON.")
    parser.add_argument("--output-dir", required=True, help="Directory for deterministic adapter coverage acceptance outputs.")
    parser.add_argument("--json", action="store_true", help="Print the store record as JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    closeout = load_json(args.fixture_pipeline_closeout_json)
    traceability = load_json(args.traceability_index_json) if args.traceability_index_json else None
    handoff = load_json(args.acceptance_handoff_json) if args.acceptance_handoff_json else None
    record = store_source_adapter_coverage_acceptance(closeout, Path(args.output_dir), traceability, handoff)
    if args.json:
        print(json.dumps(record, sort_keys=True, indent=2))
    else:
        print(
            "Source Adapter Coverage Acceptance: "
            f"{record['source_adapter_coverage_acceptance_id']} "
            f"status={record['acceptance_status']} "
            f"files={record['output_file_count']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
