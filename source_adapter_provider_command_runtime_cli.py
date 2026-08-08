from __future__ import annotations

import argparse
import json
from pathlib import Path

from source_adapter_provider_command_runtime import build_source_adapter_provider_command_runtime
from source_adapter_provider_command_runtime_store import store_source_adapter_provider_command_runtime_package


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build source adapter provider command runtime receipts.")
    parser.add_argument("--json", action="store_true", help="Print the full package as JSON.")
    parser.add_argument("--store", action="store_true", help="Store package artifacts and print store metadata.")
    parser.add_argument("--output-dir", default=None, help="Output directory for command receipts/store files.")
    args = parser.parse_args(argv)
    package = build_source_adapter_provider_command_runtime(output_root=args.output_dir).as_dict()
    if args.store:
        print(json.dumps(store_source_adapter_provider_command_runtime_package(package, Path(args.output_dir) if args.output_dir else None), indent=2, sort_keys=True))
    elif args.json:
        print(json.dumps(package, indent=2, sort_keys=True))
    else:
        summary = package["operator_summary"]
        print("Source Adapter Provider Command Runtime")
        print(f"status={summary['status']}")
        print(f"provider_command_request_row_count={summary['provider_command_request_row_count']}")
        print(f"provider_command_execution_receipt_row_count={summary['provider_command_execution_receipt_row_count']}")
        print(f"successful_execution_count={summary['successful_execution_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
