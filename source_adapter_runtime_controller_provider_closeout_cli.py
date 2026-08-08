from __future__ import annotations

import argparse
import json
from pathlib import Path

from source_adapter_runtime_controller_provider_closeout import build_source_adapter_runtime_controller_provider_closeout
from source_adapter_runtime_controller_provider_closeout_store import store_source_adapter_runtime_controller_provider_closeout
from source_adapter_runtime_controller_provider_closeout_verifier import verify_source_adapter_runtime_controller_provider_closeout


def _load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build shared source Adapter Runtime Controller Provider Closeout outputs.")
    parser.add_argument("--operator-acceptance-closeout-json", required=True)
    parser.add_argument("--output-dir")
    parser.add_argument("--operator-id", default="operator")
    parser.add_argument("--install-profile", default="source_adapter_runtime_controller_provider_install_v1")
    parser.add_argument("--capability", action="append", default=[])
    parser.add_argument("--closeout-note", action="append", default=[])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    package = build_source_adapter_runtime_controller_provider_closeout(
        _load_json(args.operator_acceptance_closeout_json),
        enabled_capabilities=args.capability or None,
        operator_id=args.operator_id,
        install_profile=args.install_profile,
        closeout_notes=args.closeout_note,
    )
    verification = verify_source_adapter_runtime_controller_provider_closeout(package)
    if args.output_dir:
        result = store_source_adapter_runtime_controller_provider_closeout(package, args.output_dir)
        print(json.dumps(result, sort_keys=True, indent=2))
    else:
        print(json.dumps({"package": package, "verification": verification}, sort_keys=True, indent=2))
    return 0 if verification["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
