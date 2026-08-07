from __future__ import annotations

import argparse
import json
from pathlib import Path

from source_artifact_collection import build_source_artifact_collection_from_files
from source_artifact_collection_store import store_source_artifact_collection


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a shared source artifact collection from explicit files.")
    parser.add_argument("--adapter-id", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--artifact", action="append", default=[], help="Explicit artifact as role=path. Repeatable.")
    parser.add_argument("--capture-job-json", type=Path)
    parser.add_argument("--operator-notes", default="")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--json", action="store_true", help="Print compact JSON instead of pretty JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    collection = build_source_artifact_collection_from_files(
        adapter_id=args.adapter_id,
        source_url=args.source_url,
        artifact_specs=args.artifact,
        capture_job_path=args.capture_job_json,
        operator_notes=args.operator_notes,
    )
    receipt = store_source_artifact_collection(collection, args.output_dir)
    if args.json:
        print(json.dumps(receipt, sort_keys=True))
    else:
        print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
