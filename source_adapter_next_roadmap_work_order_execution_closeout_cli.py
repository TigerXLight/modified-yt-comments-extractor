from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from source_adapter_next_roadmap_section_selection_closeout import example_next_roadmap_section_selection_closeout_package
from source_adapter_next_roadmap_work_order_execution_closeout import build_source_adapter_next_roadmap_work_order_execution_closeout
from source_adapter_next_roadmap_work_order_execution_closeout_store import store_source_adapter_next_roadmap_work_order_execution_closeout
from source_adapter_next_roadmap_work_order_execution_closeout_verifier import verify_source_adapter_next_roadmap_work_order_execution_closeout


def _load_json(path: str | None) -> Any:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build source adapter next roadmap work order execution closeout artifacts.")
    parser.add_argument("--next-roadmap-section-selection-json", help="Path to next roadmap section selection closeout JSON.")
    parser.add_argument("--output-dir", help="Optional output directory for stored JSON artifacts.")
    parser.add_argument("--operator-id", default="operator")
    parser.add_argument("--closeout-note", action="append", default=[])
    args = parser.parse_args(argv)
    input_package = _load_json(args.next_roadmap_section_selection_json) or example_next_roadmap_section_selection_closeout_package()
    package = build_source_adapter_next_roadmap_work_order_execution_closeout(
        input_package,
        operator_id=args.operator_id,
        closeout_notes=args.closeout_note,
    ).as_dict()
    if args.output_dir:
        result = store_source_adapter_next_roadmap_work_order_execution_closeout(package, args.output_dir)
    else:
        result = {"package": package, "verification": verify_source_adapter_next_roadmap_work_order_execution_closeout(package)}
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
