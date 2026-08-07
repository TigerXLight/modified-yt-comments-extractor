from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from source_adapter_archive_result_intake_bridge import build_source_adapter_archive_result_intake_bridge
from source_adapter_archive_result_intake_bridge_store import store_source_adapter_archive_result_intake_bridge


def _load_json(path: str | Path) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_operator_results(paths: Sequence[str]) -> object:
    values = [_load_json(path) for path in paths]
    if len(values) == 1:
        return values[0]
    return values


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build shared Adapter Archive Result Intake Bridge packages.")
    parser.add_argument("--archive-handoff-bridge-json", required=True, help="Adapter Archive Handoff Bridge package JSON.")
    parser.add_argument("--archive-result-json", action="append", required=True, help="Operator archive result JSON or grouped result JSON; may be repeated.")
    parser.add_argument("--output-dir", help="Optional output directory for bridge artifacts.")
    parser.add_argument("--operator-id", default="manual_archive_operator", help="Non-secret archive operator identifier.")
    parser.add_argument("--intake-note", action="append", default=[], help="Optional archive result intake note; may be repeated.")
    args = parser.parse_args(argv)

    bridge = _load_json(args.archive_handoff_bridge_json)
    operator_results = _load_operator_results(args.archive_result_json)
    package = build_source_adapter_archive_result_intake_bridge(
        bridge,
        operator_results,
        operator_id=args.operator_id,
        intake_notes=args.intake_note,
    )
    result = store_source_adapter_archive_result_intake_bridge(package, args.output_dir) if args.output_dir else package
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
