from __future__ import annotations

import argparse
import json

from source_adapter_registry_release_store import store_source_adapter_registry_release_from_files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a local source adapter registry release package.")
    parser.add_argument("--registry-update-package", required=True, help="Source Adapter Registry Update package JSON")
    parser.add_argument("--output-dir", required=True, help="Directory where release artifacts will be written")
    parser.add_argument("--json", action="store_true", help="Print JSON summary")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = store_source_adapter_registry_release_from_files(args.registry_update_package, args.output_dir)
    if args.json:
        print(json.dumps(summary, sort_keys=True, indent=2))
    else:
        print(f"Stored Source Adapter Registry Release: {summary['source_adapter_registry_release_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
