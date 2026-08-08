from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from source_adapter_roadmap_audit_final_closeout import (
    build_source_adapter_roadmap_audit_final_closeout,
    example_operator_named_site_smoke_execution_closeout_package,
)
from source_adapter_roadmap_audit_final_closeout_store import store_source_adapter_roadmap_audit_final_closeout
from source_adapter_roadmap_audit_final_closeout_verifier import verify_source_adapter_roadmap_audit_final_closeout


def _load_json(path: str | None, fallback: Any) -> Any:
    if not path:
        return fallback
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build shared source Adapter Roadmap Audit Final Closeout artifacts.")
    parser.add_argument("--operator-named-site-smoke-execution-closeout-json", help="Operator Named Site Smoke Execution Closeout package JSON.")
    parser.add_argument("--roadmap-sections-json", help="Optional list of additional closed roadmap section identifiers.")
    parser.add_argument("--output-dir", help="Optional output directory for stored JSON artifacts.")
    parser.add_argument("--operator-id", default="operator")
    parser.add_argument("--release-note", action="append", default=[])
    parser.add_argument("--closeout-note", action="append", default=[])
    args = parser.parse_args(argv)

    operator_closeout = _load_json(args.operator_named_site_smoke_execution_closeout_json, example_operator_named_site_smoke_execution_closeout_package())
    roadmap_sections = _load_json(args.roadmap_sections_json, None)
    package = build_source_adapter_roadmap_audit_final_closeout(
        operator_closeout,
        roadmap_sections=roadmap_sections,
        release_notes=args.release_note,
        operator_id=args.operator_id,
        closeout_notes=args.closeout_note,
    ).as_dict()
    verification = verify_source_adapter_roadmap_audit_final_closeout(package)
    if args.output_dir:
        result = store_source_adapter_roadmap_audit_final_closeout(package, args.output_dir)
    else:
        result = {"package": package, "verification": verification}
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if verification["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
