from __future__ import annotations

import argparse
import json

from source_adapter_evidence_export_runtime_bridge import example_evidence_export_runtime_bridge_package
from source_adapter_evidence_export_runtime_bridge_store import store_source_adapter_evidence_export_runtime_bridge_package
from source_adapter_evidence_export_runtime_bridge_verifier import verify_source_adapter_evidence_export_runtime_bridge_package


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build source adapter evidence/export runtime bridge artifacts.")
    parser.add_argument("--json", action="store_true", help="print full package JSON")
    parser.add_argument("--store", help="store package artifacts in this directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    package = example_evidence_export_runtime_bridge_package()
    if args.store:
        print(json.dumps(store_source_adapter_evidence_export_runtime_bridge_package(package, args.store), indent=2, sort_keys=True))
    elif args.json:
        print(json.dumps({"package": package, "verification": verify_source_adapter_evidence_export_runtime_bridge_package(package)}, indent=2, sort_keys=True))
    else:
        verification = verify_source_adapter_evidence_export_runtime_bridge_package(package)
        print("Source Adapter Evidence Export Runtime Bridge")
        print(f"status={package['evidence_export_runtime_bridge_status']}")
        print(f"handoff={verification['handoff_status']}")
        print(f"evidence_rows={verification['evidence_export_queue_row_count']}")
        print(f"issue_count={verification['issue_count']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
