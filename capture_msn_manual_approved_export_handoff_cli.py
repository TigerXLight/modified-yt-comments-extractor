from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from capture_msn_manual_approved_export_handoff import (
    build_msn_manual_approved_export_handoff,
    msn_manual_approved_export_handoff_to_json,
)
from capture_msn_manual_approved_export_handoff_store import (
    msn_manual_approved_export_handoff_store_report_to_json,
    store_msn_manual_approved_export_handoff,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build/store an MSN manual approved Total Export handoff from explicit JSON inputs.")
    parser.add_argument("--decision-json", required=True, help="Explicit MSN manual Evidence Review decision JSON file.")
    parser.add_argument("--output-dir", required=True, help="Directory where handoff JSON files will be written.")
    parser.add_argument("--package-store-json", help="Optional MSN manual Total Export package store JSON file.")
    parser.add_argument("--operator-run-id", default="operator_run")
    parser.add_argument("--print-handoff-json", action="store_true")
    return parser


def _read_json(path: str) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    package_store = _read_json(args.package_store_json) if args.package_store_json else None
    handoff = build_msn_manual_approved_export_handoff(
        _read_json(args.decision_json),
        package_store_report=package_store,
        operator_run_id=args.operator_run_id,
    )
    store_report = store_msn_manual_approved_export_handoff(handoff, args.output_dir)
    if args.print_handoff_json:
        sys.stdout.write(msn_manual_approved_export_handoff_to_json(handoff))
    else:
        sys.stdout.write(msn_manual_approved_export_handoff_store_report_to_json(store_report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
