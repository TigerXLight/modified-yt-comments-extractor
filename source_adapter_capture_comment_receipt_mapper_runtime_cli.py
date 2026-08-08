from __future__ import annotations

import argparse
import json
from pathlib import Path

from source_adapter_capture_comment_receipt_mapper_runtime import example_source_adapter_capture_comment_receipt_mapper_runtime_package
from source_adapter_capture_comment_receipt_mapper_runtime_store import store_source_adapter_capture_comment_receipt_mapper_runtime_package
from source_adapter_capture_comment_receipt_mapper_runtime_verifier import verify_source_adapter_capture_comment_receipt_mapper_runtime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build Source Adapter Capture Comment Receipt Mapper Runtime artifacts.")
    parser.add_argument("--operator-id", default="operator")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    package = example_source_adapter_capture_comment_receipt_mapper_runtime_package(operator_id=args.operator_id)
    result = {"package": package, "verification": verify_source_adapter_capture_comment_receipt_mapper_runtime(package)} if args.verify else package
    if args.output_dir:
        result = {"package": package, "store": store_source_adapter_capture_comment_receipt_mapper_runtime_package(package, Path(args.output_dir)), "verification": verify_source_adapter_capture_comment_receipt_mapper_runtime(package)}
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("Source Adapter Capture Comment Receipt Mapper Runtime built: " + package["id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
