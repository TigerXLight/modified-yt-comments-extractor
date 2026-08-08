from __future__ import annotations

import argparse
import json

from source_adapter_operator_delivery_receipt_closeout import example_operator_delivery_receipt_closeout_package
from source_adapter_operator_delivery_receipt_closeout_store import store_source_adapter_operator_delivery_receipt_closeout_package
from source_adapter_operator_delivery_receipt_closeout_verifier import verify_source_adapter_operator_delivery_receipt_closeout_package

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Review source adapter delivery receipts and build operator closeout.")
    p.add_argument("--json", action="store_true")
    p.add_argument("--store", help="store closeout artifacts in this directory")
    return p

def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    package = example_operator_delivery_receipt_closeout_package()
    if args.store:
        print(json.dumps(store_source_adapter_operator_delivery_receipt_closeout_package(package, args.store), indent=2, sort_keys=True))
    elif args.json:
        print(json.dumps({"package": package, "verification": verify_source_adapter_operator_delivery_receipt_closeout_package(package)}, indent=2, sort_keys=True))
    else:
        verification = verify_source_adapter_operator_delivery_receipt_closeout_package(package)
        print("Source Adapter Operator Delivery Receipt Closeout")
        print(f"status={package['operator_delivery_receipt_closeout_status']}")
        print(f"handoff={verification['handoff_status']}")
        print(f"review_rows={verification['operator_delivery_receipt_review_row_count']}")
        print(f"release_ready={verification['release_section_completion_ready']}")
        print(f"issue_count={verification['issue_count']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
