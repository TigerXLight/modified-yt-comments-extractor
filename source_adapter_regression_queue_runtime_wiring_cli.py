from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from source_adapter_priority_fixture_regression_promotion import example_priority_fixture_regression_promotion_package
from source_adapter_regression_queue_runtime_wiring import build_source_adapter_regression_queue_runtime_wiring
from source_adapter_regression_queue_runtime_wiring_store import store_source_adapter_regression_queue_runtime_wiring
from source_adapter_regression_queue_runtime_wiring_verifier import verify_source_adapter_regression_queue_runtime_wiring
from source_adapter_runtime_gui_provider_implementation import example_runtime_gui_provider_implementation_package


def _load_json(path: str | None) -> Any:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install promoted source-adapter regression queue rows into local runtime wiring artifacts.")
    parser.add_argument("--priority-fixture-regression-promotion-json", help="Path to priority fixture regression promotion JSON.")
    parser.add_argument("--runtime-gui-provider-implementation-json", help="Path to runtime GUI provider implementation JSON.")
    parser.add_argument("--output-dir", help="Optional output directory for stored JSON artifacts.")
    parser.add_argument("--operator-id", default="operator")
    parser.add_argument("--wiring-note", action="append", default=[])
    args = parser.parse_args(argv)
    promotion_package = _load_json(args.priority_fixture_regression_promotion_json) or example_priority_fixture_regression_promotion_package()
    runtime_package = _load_json(args.runtime_gui_provider_implementation_json) or example_runtime_gui_provider_implementation_package()
    package = build_source_adapter_regression_queue_runtime_wiring(
        promotion_package,
        runtime_package,
        operator_id=args.operator_id,
        wiring_notes=args.wiring_note,
    ).as_dict()
    if args.output_dir:
        result = store_source_adapter_regression_queue_runtime_wiring(package, args.output_dir)
    else:
        result = {"package": package, "verification": verify_source_adapter_regression_queue_runtime_wiring(package)}
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
