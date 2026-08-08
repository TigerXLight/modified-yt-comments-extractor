from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from source_adapter_operator_approved_execution_runtime import example_operator_approved_execution_runtime_package
from source_adapter_provider_backend_interfaces import build_source_adapter_provider_backend_interfaces
from source_adapter_provider_backend_interfaces_store import store_source_adapter_provider_backend_interfaces
from source_adapter_provider_backend_interfaces_verifier import verify_source_adapter_provider_backend_interfaces


def _load_json(path: str | None) -> Any:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build and execute source-adapter provider backend interface receipts.")
    parser.add_argument("--operator-runtime-json", help="Path to operator approved execution runtime JSON.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--operator-id", default="operator")
    parser.add_argument("--execution-note", action="append", default=[])
    args = parser.parse_args(argv)
    runtime_package = _load_json(args.operator_runtime_json) or example_operator_approved_execution_runtime_package()
    package = build_source_adapter_provider_backend_interfaces(runtime_package, output_dir=args.output_dir, operator_id=args.operator_id, execution_notes=args.execution_note).as_dict()
    result = store_source_adapter_provider_backend_interfaces(package, args.output_dir)
    result["package"] = package
    result["verification"] = verify_source_adapter_provider_backend_interfaces(package)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
