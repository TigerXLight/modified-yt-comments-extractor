from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from source_adapter_fixture_pipeline_closeout import load_json
from source_adapter_fixture_pipeline_closeout_store import store_source_adapter_fixture_pipeline_closeout


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Close a local-only shared source adapter fixture pipeline package.")
    parser.add_argument("--fixture-pipeline-json", required=True, help="Source Adapter Fixture Pipeline package JSON.")
    parser.add_argument("--pipeline-store-json", help="Optional Source Adapter Fixture Pipeline store record JSON.")
    parser.add_argument("--output-dir", required=True, help="Directory for deterministic fixture pipeline closeout outputs.")
    parser.add_argument("--json", action="store_true", help="Print the store record as JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    fixture_pipeline = load_json(args.fixture_pipeline_json)
    pipeline_store = load_json(args.pipeline_store_json) if args.pipeline_store_json else None
    record = store_source_adapter_fixture_pipeline_closeout(fixture_pipeline, Path(args.output_dir), pipeline_store)
    if args.json:
        print(json.dumps(record, sort_keys=True, indent=2))
    else:
        print(
            "Source Adapter Fixture Pipeline Closeout: "
            f"{record['source_adapter_fixture_pipeline_closeout_id']} "
            f"status={record['closeout_status']} "
            f"files={record['output_file_count']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
