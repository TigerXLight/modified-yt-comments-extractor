from __future__ import annotations

import argparse
import json
from pathlib import Path

from source_adapter_ultimate_delivery_bundle_closeout import example_source_adapter_ultimate_delivery_bundle_closeout_package
from source_adapter_ultimate_delivery_bundle_closeout_store import store_source_adapter_ultimate_delivery_bundle_closeout_package
from source_adapter_ultimate_delivery_bundle_closeout_verifier import verify_source_adapter_ultimate_delivery_bundle_closeout


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build Source Adapter Ultimate Delivery Bundle Closeout artifacts.")
    parser.add_argument("--operator-id", default="operator")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    package = example_source_adapter_ultimate_delivery_bundle_closeout_package(operator_id=args.operator_id)
    result = {"package": package, "verification": verify_source_adapter_ultimate_delivery_bundle_closeout(package)} if args.verify else package
    if args.output_dir:
        result = {"package": package, "store": store_source_adapter_ultimate_delivery_bundle_closeout_package(package, Path(args.output_dir)), "verification": verify_source_adapter_ultimate_delivery_bundle_closeout(package)}
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("Source Adapter Ultimate Delivery Bundle Closeout built: " + package["id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
