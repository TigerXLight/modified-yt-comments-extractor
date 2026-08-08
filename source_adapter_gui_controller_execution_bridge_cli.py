from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from source_adapter_gui_controller_execution_bridge import build_source_adapter_gui_controller_execution_bridge
from source_adapter_gui_controller_execution_bridge_store import store_source_adapter_gui_controller_execution_bridge
from source_adapter_gui_controller_execution_bridge_verifier import verify_source_adapter_gui_controller_execution_bridge
from source_adapter_operator_approved_execution_runtime import example_operator_approved_execution_runtime_package
from source_adapter_provider_backend_interfaces import build_source_adapter_provider_backend_interfaces


def _load_json(path: str | None) -> Any:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build source-adapter GUI/controller execution bridge receipts.")
    parser.add_argument("--operator-runtime-json")
    parser.add_argument("--provider-backend-json")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--operator-id", default="operator")
    parser.add_argument("--execution-note", action="append", default=[])
    args = parser.parse_args(argv)
    operator_runtime = _load_json(args.operator_runtime_json) or example_operator_approved_execution_runtime_package()
    provider_backend = _load_json(args.provider_backend_json) or build_source_adapter_provider_backend_interfaces(operator_runtime, output_dir=args.output_dir).as_dict()
    package = build_source_adapter_gui_controller_execution_bridge(operator_runtime, provider_backend, output_dir=args.output_dir, operator_id=args.operator_id, execution_notes=args.execution_note).as_dict()
    result = store_source_adapter_gui_controller_execution_bridge(package, args.output_dir)
    result["package"] = package
    result["verification"] = verify_source_adapter_gui_controller_execution_bridge(package)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
