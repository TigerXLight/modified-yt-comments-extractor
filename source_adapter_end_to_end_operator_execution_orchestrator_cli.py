from __future__ import annotations

import argparse
import json

from source_adapter_end_to_end_operator_execution_orchestrator import example_end_to_end_operator_execution_orchestrator_package
from source_adapter_end_to_end_operator_execution_orchestrator_store import store_source_adapter_end_to_end_operator_execution_orchestrator_package
from source_adapter_end_to_end_operator_execution_orchestrator_verifier import verify_source_adapter_end_to_end_operator_execution_orchestrator_package


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Source Adapter End-to-End Operator Execution Orchestrator")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--store-dir", default=None)
    args = parser.parse_args(argv)
    package = example_end_to_end_operator_execution_orchestrator_package()
    verification = verify_source_adapter_end_to_end_operator_execution_orchestrator_package(package)
    result = {"package": package, "verification": verification}
    if args.store_dir:
        result["store"] = store_source_adapter_end_to_end_operator_execution_orchestrator_package(package, args.store_dir)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("Source Adapter End-to-End Operator Execution Orchestrator: " + package["status"])
        print("handoff: " + package["handoff"]["handoff_status"])
        print("issues: " + str(verification["issue_count"]))
    return 0 if verification["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
