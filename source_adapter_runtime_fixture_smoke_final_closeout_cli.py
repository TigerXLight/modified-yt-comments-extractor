from __future__ import annotations

import argparse
import json
from pathlib import Path

from source_adapter_runtime_fixture_smoke_final_closeout import build_source_adapter_runtime_fixture_smoke_final_closeout
from source_adapter_runtime_fixture_smoke_final_closeout_store import store_source_adapter_runtime_fixture_smoke_final_closeout
from source_adapter_runtime_fixture_smoke_final_closeout_verifier import verify_source_adapter_runtime_fixture_smoke_final_closeout


def _load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build shared source Adapter Runtime Fixture Smoke Final Closeout outputs.")
    parser.add_argument("--controller-provider-closeout-json", required=True)
    parser.add_argument("--output-dir")
    parser.add_argument("--operator-id", default="operator")
    parser.add_argument("--capability", action="append", default=[])
    parser.add_argument("--closeout-note", action="append", default=[])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    package = build_source_adapter_runtime_fixture_smoke_final_closeout(
        _load_json(args.controller_provider_closeout_json),
        enabled_capabilities=args.capability or None,
        operator_id=args.operator_id,
        closeout_notes=args.closeout_note,
    )
    verification = verify_source_adapter_runtime_fixture_smoke_final_closeout(package)
    if args.output_dir:
        result = store_source_adapter_runtime_fixture_smoke_final_closeout(package, args.output_dir)
        print(json.dumps(result, sort_keys=True, indent=2))
    else:
        print(json.dumps({"package": package, "verification": verification}, sort_keys=True, indent=2))
    return 0 if verification["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
