from __future__ import annotations

import argparse
import json

from source_adapter_registry_rollout_store import store_source_adapter_registry_rollout_from_files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a local source adapter registry rollout package.")
    parser.add_argument("--registry-release-package", required=True, help="Source Adapter Registry Release package JSON")
    parser.add_argument("--output-dir", required=True, help="Directory where rollout artifacts will be written")
    parser.add_argument("--json", action="store_true", help="Print JSON summary")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = store_source_adapter_registry_rollout_from_files(args.registry_release_package, args.output_dir)
    if args.json:
        print(json.dumps(summary, sort_keys=True, indent=2))
    else:
        print(f"Stored Source Adapter Registry Rollout: {summary['source_adapter_registry_rollout_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
