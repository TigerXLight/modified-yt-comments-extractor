from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from capture_msn_manual_release_section_closeout import (
    build_msn_manual_release_section_closeout,
    msn_manual_release_section_closeout_to_json,
)
from capture_msn_manual_release_section_closeout_store import (
    msn_manual_release_section_closeout_store_report_to_json,
    store_msn_manual_release_section_closeout,
)


def _read_json(path: str) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise SystemExit(f"JSON file must contain an object: {path}")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Close out an MSN manual release section from an explicit release export bundle JSON file.")
    parser.add_argument("--release-export-bundle", required=True, help="Path to explicit MSN manual release export bundle JSON")
    parser.add_argument("--release-export-bundle-store", help="Optional path to release export bundle store JSON")
    parser.add_argument("--output-dir", required=True, help="Directory for release closeout JSON outputs")
    parser.add_argument("--closeout-label", default="operator_release_section_closeout")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    release_export_bundle = _read_json(args.release_export_bundle)
    store_payload = _read_json(args.release_export_bundle_store) if args.release_export_bundle_store else None
    report = build_msn_manual_release_section_closeout(
        release_export_bundle,
        release_export_bundle_store_report=store_payload,
        closeout_label=args.closeout_label,
    )
    store_report = store_msn_manual_release_section_closeout(report, args.output_dir)
    print(json.dumps(msn_manual_release_section_closeout_store_report_to_json(store_report), indent=2, sort_keys=True))
    if not report.ready_for_section_closeout:
        print(json.dumps(msn_manual_release_section_closeout_to_json(report), indent=2, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
