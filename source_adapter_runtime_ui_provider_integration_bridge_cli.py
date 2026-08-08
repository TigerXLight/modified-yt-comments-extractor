from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from source_adapter_runtime_ui_provider_integration_bridge import build_source_adapter_runtime_ui_provider_integration_bridge
from source_adapter_runtime_ui_provider_integration_bridge_store import store_source_adapter_runtime_ui_provider_integration_bridge


def _load_json(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the shared source adapter Runtime UI Provider Integration Bridge.")
    parser.add_argument("--runtime-receipt-review-bridge-json", required=True)
    parser.add_argument("--output-dir")
    parser.add_argument("--operator-id", default="operator")
    parser.add_argument("--integration-profile", default="source_adapter_runtime_ui_provider_integration_v1")
    parser.add_argument("--capability", action="append", dest="enabled_capabilities")
    parser.add_argument("--integration-note", action="append", dest="integration_notes")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    package = build_source_adapter_runtime_ui_provider_integration_bridge(
        _load_json(args.runtime_receipt_review_bridge_json),
        enabled_capabilities=args.enabled_capabilities,
        integration_profile=args.integration_profile,
        operator_id=args.operator_id,
        integration_notes=args.integration_notes,
    )
    if args.output_dir:
        print(json.dumps(store_source_adapter_runtime_ui_provider_integration_bridge(package, args.output_dir), indent=2, sort_keys=True, ensure_ascii=False))
    else:
        print(json.dumps(package, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
