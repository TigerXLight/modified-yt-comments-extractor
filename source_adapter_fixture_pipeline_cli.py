from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from source_adapter_fixture_pipeline import load_json
from source_adapter_fixture_pipeline_store import store_source_adapter_fixture_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a local-only shared source adapter fixture pipeline package.")
    parser.add_argument("--fixture-review-json", required=True, help="Adapter Fixture Review package JSON.")
    parser.add_argument("--pipeline-results-json", help="Optional explicit local fixture pipeline results JSON.")
    parser.add_argument("--output-dir", required=True, help="Directory for deterministic fixture pipeline outputs.")
    parser.add_argument("--json", action="store_true", help="Print the store record as JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    fixture_review = load_json(args.fixture_review_json)
    pipeline_results = load_json(args.pipeline_results_json) if args.pipeline_results_json else None
    record = store_source_adapter_fixture_pipeline(fixture_review, Path(args.output_dir), pipeline_results)
    if args.json:
        print(json.dumps(record, sort_keys=True, indent=2))
    else:
        print(
            "Source Adapter Fixture Pipeline: "
            f"{record['source_adapter_fixture_pipeline_id']} "
            f"status={record['fixture_pipeline_status']} "
            f"files={record['output_file_count']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
