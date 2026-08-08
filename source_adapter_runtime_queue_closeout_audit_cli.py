from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from source_adapter_regression_queue_runtime_wiring import example_regression_queue_runtime_wiring_package
from source_adapter_runtime_queue_closeout_audit import build_source_adapter_runtime_queue_closeout_audit
from source_adapter_runtime_queue_closeout_audit_store import store_source_adapter_runtime_queue_closeout_audit
from source_adapter_runtime_queue_closeout_audit_verifier import verify_source_adapter_runtime_queue_closeout_audit


def _load_json(path: str | None) -> Any:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a local-only source-adapter runtime queue closeout audit package.")
    parser.add_argument("--runtime-wiring-json", help="Path to source adapter regression queue runtime wiring JSON.")
    parser.add_argument("--output-dir", help="Optional output directory for stored JSON artifacts.")
    parser.add_argument("--operator-id", default="operator")
    parser.add_argument("--closeout-note", action="append", default=[])
    args = parser.parse_args(argv)
    runtime_wiring = _load_json(args.runtime_wiring_json) or example_regression_queue_runtime_wiring_package()
    package = build_source_adapter_runtime_queue_closeout_audit(
        runtime_wiring,
        operator_id=args.operator_id,
        closeout_notes=args.closeout_note,
    ).as_dict()
    if args.output_dir:
        result = store_source_adapter_runtime_queue_closeout_audit(package, args.output_dir)
    else:
        result = {"package": package, "verification": verify_source_adapter_runtime_queue_closeout_audit(package)}
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
