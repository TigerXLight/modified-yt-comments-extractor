from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from source_adapter_registry_update_store import store_source_adapter_registry_update_from_files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a local-only source adapter registry update package.")
    parser.add_argument("--adapter-registry-handoff", required=True)
    parser.add_argument("--existing-registry")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = store_source_adapter_registry_update_from_files(
        args.adapter_registry_handoff,
        Path(args.output_dir),
        existing_registry_path=args.existing_registry,
    )
    if args.json:
        print(json.dumps(summary, sort_keys=True, indent=2, ensure_ascii=False))
    else:
        print(
            f"Source Adapter Registry Update: {summary['registry_update_status']} "
            f"({summary['output_file_count']} files)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
