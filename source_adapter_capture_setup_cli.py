from __future__ import annotations

import argparse
import json
from pathlib import Path

from source_adapter_capture_setup import build_source_adapter_capture_setup, demo_source_selection_package, load_json
from source_adapter_capture_setup_store import store_source_adapter_capture_setup
from source_adapter_capture_setup_verifier import verify_source_adapter_capture_setup_package


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a local source adapter capture setup package.")
    parser.add_argument("--source-selection-package", help="Path to a source adapter source selection package JSON.")
    parser.add_argument("--output-dir", help="Optional directory where deterministic output JSON files are written.")
    parser.add_argument("--verify", action="store_true", help="Print verifier output instead of the package.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    selection_package = load_json(args.source_selection_package) if args.source_selection_package else demo_source_selection_package()
    if args.output_dir:
        result = store_source_adapter_capture_setup(selection_package, Path(args.output_dir))
    else:
        package = build_source_adapter_capture_setup(selection_package)
        result = verify_source_adapter_capture_setup_package(package) if args.verify else package
    print(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
