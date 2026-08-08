from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from source_adapter_operator_named_site_smoke_execution_closeout import (
    build_source_adapter_operator_named_site_smoke_execution_closeout,
    example_priority_site_pack_execution_closeout_package,
)
from source_adapter_operator_named_site_smoke_execution_closeout_store import store_source_adapter_operator_named_site_smoke_execution_closeout
from source_adapter_operator_named_site_smoke_execution_closeout_verifier import verify_source_adapter_operator_named_site_smoke_execution_closeout


def _load_json(path: str | None, fallback: Any) -> Any:
    if not path:
        return fallback
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build shared source Adapter Operator Named Site Smoke Execution Closeout artifacts.")
    parser.add_argument("--priority-site-pack-execution-closeout-json", help="Priority Site Pack Execution Closeout package JSON.")
    parser.add_argument("--named-site-selections-json", help="Optional named-site selection mapping/list JSON.")
    parser.add_argument("--manual-smoke-receipts-json", help="Optional manual smoke receipt overrides mapping/list JSON.")
    parser.add_argument("--output-dir", help="Optional output directory for stored JSON artifacts.")
    parser.add_argument("--operator-id", default="operator")
    parser.add_argument("--closeout-note", action="append", default=[])
    args = parser.parse_args(argv)

    priority_closeout = _load_json(args.priority_site_pack_execution_closeout_json, example_priority_site_pack_execution_closeout_package())
    named_site_selections = _load_json(args.named_site_selections_json, None)
    manual_smoke_receipts = _load_json(args.manual_smoke_receipts_json, None)
    package = build_source_adapter_operator_named_site_smoke_execution_closeout(
        priority_closeout,
        named_site_selections=named_site_selections,
        manual_smoke_receipts=manual_smoke_receipts,
        operator_id=args.operator_id,
        closeout_notes=args.closeout_note,
    ).as_dict()
    verification = verify_source_adapter_operator_named_site_smoke_execution_closeout(package)
    if args.output_dir:
        result = store_source_adapter_operator_named_site_smoke_execution_closeout(package, args.output_dir)
    else:
        result = {"package": package, "verification": verification}
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if verification["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
