from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from capture_msn_manual_release_export_bundle import (
    build_msn_manual_release_export_bundle,
    msn_manual_release_export_bundle_to_json,
)
from capture_msn_manual_release_export_bundle_store import (
    msn_manual_release_export_bundle_store_report_to_json,
    store_msn_manual_release_export_bundle,
)


def _read_json(path: str) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise SystemExit(f"JSON file must contain an object: {path}")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build an MSN manual release export bundle from an explicit release index JSON file.")
    parser.add_argument("--release-index", required=True, help="Path to explicit MSN manual release index JSON")
    parser.add_argument("--release-index-store", help="Optional path to release index store JSON")
    parser.add_argument("--output-dir", required=True, help="Directory for export bundle JSON outputs")
    parser.add_argument("--export-label", default="operator_total_export_handoff")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    release_index = _read_json(args.release_index)
    store_payload = _read_json(args.release_index_store) if args.release_index_store else None
    report = build_msn_manual_release_export_bundle(release_index, release_index_store_report=store_payload, export_label=args.export_label)
    store_report = store_msn_manual_release_export_bundle(report, args.output_dir)
    print(json.dumps(msn_manual_release_export_bundle_store_report_to_json(store_report), indent=2, sort_keys=True))
    if not report.ready_for_total_export_handoff:
        print(json.dumps(msn_manual_release_export_bundle_to_json(report), indent=2, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
