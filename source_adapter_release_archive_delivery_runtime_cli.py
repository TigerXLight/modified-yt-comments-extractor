from __future__ import annotations

import argparse
import json

from source_adapter_release_archive_delivery_runtime import build_source_adapter_release_archive_delivery_runtime
from source_adapter_release_archive_delivery_runtime_store import store_source_adapter_release_archive_delivery_runtime_package
from source_adapter_release_archive_delivery_runtime_verifier import verify_source_adapter_release_archive_delivery_runtime_package

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Execute source adapter release/archive delivery runtime.")
    p.add_argument("--json", action="store_true")
    p.add_argument("--output-dir", help="delivery output directory")
    p.add_argument("--store", help="store summary artifacts in this directory")
    return p

def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    package = build_source_adapter_release_archive_delivery_runtime(output_dir=args.output_dir).as_dict()
    if args.store:
        print(json.dumps(store_source_adapter_release_archive_delivery_runtime_package(package, args.store), indent=2, sort_keys=True))
    elif args.json:
        print(json.dumps({"package": package, "verification": verify_source_adapter_release_archive_delivery_runtime_package(package)}, indent=2, sort_keys=True))
    else:
        verification = verify_source_adapter_release_archive_delivery_runtime_package(package)
        print("Source Adapter Release Archive Delivery Runtime")
        print(f"status={package['release_archive_delivery_runtime_status']}")
        print(f"handoff={verification['handoff_status']}")
        print(f"delivery_receipts={verification['delivery_receipt_row_count']}")
        print(f"issue_count={verification['issue_count']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
