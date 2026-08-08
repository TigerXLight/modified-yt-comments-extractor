from __future__ import annotations

import argparse
import json
from pathlib import Path

from source_adapter_named_site_smoke_execution import build_source_adapter_named_site_smoke_execution
from source_adapter_named_site_smoke_execution_store import store_source_adapter_named_site_smoke_execution_package


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Execute source adapter named-site smoke package.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--store", action="store_true")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args(argv)
    package = build_source_adapter_named_site_smoke_execution(output_dir=args.output_dir).as_dict()
    if args.store:
        print(json.dumps(store_source_adapter_named_site_smoke_execution_package(package, Path(args.output_dir) if args.output_dir else None), indent=2, sort_keys=True))
    elif args.json:
        print(json.dumps(package, indent=2, sort_keys=True))
    else:
        summary = package["operator_summary"]
        print("Source Adapter Named-Site Smoke Execution")
        print(f"status={summary['status']}")
        print(f"named_site_execution_site_count={summary['named_site_execution_site_count']}")
        print(f"named_site_provider_action_receipt_row_count={summary['named_site_provider_action_receipt_row_count']}")
        print(f"successful_action_receipt_count={summary['successful_action_receipt_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
