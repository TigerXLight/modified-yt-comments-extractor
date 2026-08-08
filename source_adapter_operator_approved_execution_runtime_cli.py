from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from source_adapter_operator_approved_execution_runtime import (
    build_source_adapter_operator_approved_execution_runtime,
    example_operator_inputs,
)
from source_adapter_operator_approved_execution_runtime_store import store_source_adapter_operator_approved_execution_runtime
from source_adapter_operator_approved_execution_runtime_verifier import verify_source_adapter_operator_approved_execution_runtime
from source_adapter_regression_queue_runtime_wiring import example_regression_queue_runtime_wiring_package
from source_adapter_runtime_queue_closeout_audit import example_runtime_queue_closeout_audit_package


def _load_json(path: str | None) -> Any:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Execute the operator-approved source-adapter runtime with local provider adapters.")
    parser.add_argument("--closeout-json", help="Path to runtime queue closeout audit JSON.")
    parser.add_argument("--runtime-wiring-json", help="Path to regression queue runtime wiring JSON.")
    parser.add_argument("--operator-inputs-json", help="Path to operator named-site input JSON array.")
    parser.add_argument("--output-dir", required=True, help="Output directory for execution receipts and stored package artifacts.")
    parser.add_argument("--operator-id", default="operator")
    parser.add_argument("--execution-note", action="append", default=[])
    parser.add_argument("--use-example-inputs", action="store_true", help="Use deterministic example operator inputs when no input JSON is supplied.")
    args = parser.parse_args(argv)

    runtime_wiring = _load_json(args.runtime_wiring_json) or example_regression_queue_runtime_wiring_package()
    closeout = _load_json(args.closeout_json) or example_runtime_queue_closeout_audit_package()
    operator_inputs = _load_json(args.operator_inputs_json)
    if operator_inputs is None and args.use_example_inputs:
        operator_inputs = example_operator_inputs(runtime_wiring, receipt_root=args.output_dir)
    package = build_source_adapter_operator_approved_execution_runtime(
        closeout,
        runtime_wiring,
        operator_inputs=operator_inputs,
        output_dir=args.output_dir,
        operator_id=args.operator_id,
        execution_notes=args.execution_note,
    ).as_dict()
    result = store_source_adapter_operator_approved_execution_runtime(package, args.output_dir)
    result["package"] = package
    result["verification"] = verify_source_adapter_operator_approved_execution_runtime(package)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
