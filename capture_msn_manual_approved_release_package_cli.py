from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from capture_msn_manual_approved_release_package import (
    build_msn_manual_approved_release_package,
    msn_manual_approved_release_package_to_json,
)
from capture_msn_manual_approved_release_package_store import (
    msn_manual_approved_release_package_store_report_to_json,
    store_msn_manual_approved_release_package,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build/store an approved MSN manual Total Export release package from explicit JSON inputs.")
    parser.add_argument("--approved-handoff-json", required=True, help="Explicit MSN manual approved export handoff JSON file.")
    parser.add_argument("--output-dir", required=True, help="Directory where release package JSON files will be written.")
    parser.add_argument("--package-store-json", help="Optional MSN manual Total Export package store JSON file.")
    parser.add_argument("--release-label", default="operator_release")
    parser.add_argument("--print-release-json", action="store_true")
    return parser


def _read_json(path: str) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    package_store = _read_json(args.package_store_json) if args.package_store_json else None
    release_package = build_msn_manual_approved_release_package(
        _read_json(args.approved_handoff_json),
        package_store_report=package_store,
        release_label=args.release_label,
    )
    store_report = store_msn_manual_approved_release_package(release_package, args.output_dir)
    if args.print_release_json:
        sys.stdout.write(msn_manual_approved_release_package_to_json(release_package))
    else:
        sys.stdout.write(msn_manual_approved_release_package_store_report_to_json(store_report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
