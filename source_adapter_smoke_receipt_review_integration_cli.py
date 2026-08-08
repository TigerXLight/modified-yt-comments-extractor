from __future__ import annotations

import argparse
import json
from pathlib import Path

from source_adapter_smoke_receipt_review_integration import build_source_adapter_smoke_receipt_review_integration
from source_adapter_smoke_receipt_review_integration_store import store_source_adapter_smoke_receipt_review_integration_package


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Review and integrate source adapter smoke receipts.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--store", action="store_true")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args(argv)
    package = build_source_adapter_smoke_receipt_review_integration().as_dict()
    if args.store:
        print(json.dumps(store_source_adapter_smoke_receipt_review_integration_package(package, Path(args.output_dir) if args.output_dir else None), indent=2, sort_keys=True))
    elif args.json:
        print(json.dumps(package, indent=2, sort_keys=True))
    else:
        summary = package["operator_summary"]
        print("Source Adapter Smoke Receipt Review Integration")
        print(f"status={summary['status']}")
        print(f"smoke_receipt_review_decision_row_count={summary['smoke_receipt_review_decision_row_count']}")
        print(f"smoke_receipt_evidence_integration_row_count={summary['smoke_receipt_evidence_integration_row_count']}")
        print(f"ready_for_release_export_integration={summary['ready_for_release_export_integration']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
