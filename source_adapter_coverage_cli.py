from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from source_adapter_coverage import build_source_adapter_coverage, coverage_report_to_json, load_adapter_specs
from source_adapter_coverage_store import store_source_adapter_coverage
from source_adapter_coverage_verifier import verify_source_adapter_coverage


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build shared Source Adapter coverage reports.")
    parser.add_argument("--adapter-spec", action="append", required=True, help="JSON file containing one adapter, a list of adapters, or an adapters list.")
    parser.add_argument("--output-dir", required=True, help="Directory where coverage artifacts will be written.")
    parser.add_argument("--disable-lightweight-browser", action="store_true", help="Do not include the shared lightweight in-app browser plan.")
    parser.add_argument("--print-report", action="store_true", help="Print the coverage report rather than the store receipt.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    specs = []
    for path in args.adapter_spec:
        specs.extend(load_adapter_specs(path))
    report = build_source_adapter_coverage(specs, include_lightweight_browser=not args.disable_lightweight_browser)
    verification = verify_source_adapter_coverage(report.to_dict())
    if not verification["verified"]:
        print(json.dumps(verification, indent=2, sort_keys=True, ensure_ascii=False))
        return 2
    if args.print_report:
        print(coverage_report_to_json(report), end="")
        return 0
    receipt = store_source_adapter_coverage(report, Path(args.output_dir))
    receipt["verification"] = verification
    print(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
