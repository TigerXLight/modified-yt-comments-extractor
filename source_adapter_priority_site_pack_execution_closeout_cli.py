from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from source_adapter_priority_site_pack_execution_closeout import (
    build_source_adapter_priority_site_pack_execution_closeout,
    example_runtime_fixture_smoke_final_closeout_package,
)
from source_adapter_priority_site_pack_execution_closeout_store import store_source_adapter_priority_site_pack_execution_closeout
from source_adapter_priority_site_pack_execution_closeout_verifier import verify_source_adapter_priority_site_pack_execution_closeout


def _load_json(path: str | None, fallback: Any) -> Any:
    if not path:
        return fallback
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build shared source Adapter Priority Site Pack Execution Closeout artifacts.")
    parser.add_argument("--runtime-fixture-smoke-final-closeout-json", help="Runtime Fixture Smoke Final Closeout package JSON.")
    parser.add_argument("--priority-site-packs-json", help="Optional priority site pack list JSON.")
    parser.add_argument("--output-dir", help="Optional output directory for stored JSON artifacts.")
    parser.add_argument("--operator-id", default="operator")
    parser.add_argument("--closeout-note", action="append", default=[])
    args = parser.parse_args(argv)

    final_closeout = _load_json(args.runtime_fixture_smoke_final_closeout_json, example_runtime_fixture_smoke_final_closeout_package())
    priority_site_packs = _load_json(args.priority_site_packs_json, None)
    closeout = build_source_adapter_priority_site_pack_execution_closeout(
        final_closeout,
        priority_site_packs=priority_site_packs,
        operator_id=args.operator_id,
        closeout_notes=args.closeout_note,
    ).as_dict()
    verification = verify_source_adapter_priority_site_pack_execution_closeout(closeout)
    if args.output_dir:
        result = store_source_adapter_priority_site_pack_execution_closeout(closeout, args.output_dir)
    else:
        result = {"package": closeout, "verification": verification}
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if verification["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
