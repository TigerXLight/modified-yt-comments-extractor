from __future__ import annotations

import argparse
import json
from pathlib import Path

from source_adapter_runbook_command_export_runtime import build_package, write_package


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build Runbook Command Export Runtime package")
    parser.add_argument("--operator-id", default="operator")
    parser.add_argument("--output-dir")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.output_dir:
        result = write_package(Path(args.output_dir), operator_id=args.operator_id)
    else:
        result = build_package(operator_id=args.operator_id)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("Source Adapter Runbook Command Export Runtime CLI self-test package built")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
