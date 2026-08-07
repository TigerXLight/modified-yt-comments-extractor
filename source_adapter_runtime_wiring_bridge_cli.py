from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from source_adapter_runtime_wiring_bridge import build_source_adapter_runtime_wiring_bridge
from source_adapter_runtime_wiring_bridge_store import store_source_adapter_runtime_wiring_bridge


def _load_json(path: str | Path) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build shared Adapter Runtime Wiring Bridge packages.")
    parser.add_argument("--pipeline-closeout-bridge-json", required=True, help="Adapter Pipeline Closeout Bridge package JSON.")
    parser.add_argument("--output-dir", help="Optional output directory for bridge artifacts.")
    parser.add_argument("--execution-mode", choices=["plan_only", "dry_run"], default="dry_run")
    parser.add_argument("--operator-approval-id", default="", help="Named approval record for runtime actions.")
    parser.add_argument("--runtime-inputs-json", help="Optional runtime target inputs keyed by closeout id or adapter id.")
    parser.add_argument("--enable-capability", action="append", default=None, help="Capability to include; repeat to narrow the default catalog.")
    parser.add_argument("--operator-note", action="append", default=[], help="Optional runtime wiring note; may be repeated.")
    args = parser.parse_args(argv)

    closeout = _load_json(args.pipeline_closeout_bridge_json)
    runtime_inputs = _load_json(args.runtime_inputs_json) if args.runtime_inputs_json else {}
    package = build_source_adapter_runtime_wiring_bridge(
        closeout,
        enabled_capabilities=args.enable_capability,
        execution_mode=args.execution_mode,
        operator_approval_id=args.operator_approval_id,
        runtime_inputs=runtime_inputs,
        operator_notes=args.operator_note,
    )
    result = store_source_adapter_runtime_wiring_bridge(package, args.output_dir) if args.output_dir else package
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
