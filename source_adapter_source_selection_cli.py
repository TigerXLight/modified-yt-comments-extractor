from __future__ import annotations

import argparse
import json
from pathlib import Path

from source_adapter_source_selection import build_source_adapter_source_selection, demo_rollout_package, load_json
from source_adapter_source_selection_store import store_source_adapter_source_selection
from source_adapter_source_selection_verifier import verify_source_adapter_source_selection_package


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a local source adapter source-selection package.")
    parser.add_argument("--rollout-package", help="Path to a source adapter registry rollout package JSON.")
    parser.add_argument("--output-dir", help="Optional directory where deterministic output JSON files are written.")
    parser.add_argument("--verify", action="store_true", help="Print verifier output instead of the package.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    rollout_package = load_json(args.rollout_package) if args.rollout_package else demo_rollout_package()
    if args.output_dir:
        result = store_source_adapter_source_selection(rollout_package, Path(args.output_dir))
    else:
        package = build_source_adapter_source_selection(rollout_package)
        result = verify_source_adapter_source_selection_package(package) if args.verify else package
    print(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
