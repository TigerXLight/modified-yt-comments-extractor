from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from capture_msn_manual_release_index import build_msn_manual_release_index, msn_manual_release_index_to_json
from capture_msn_manual_release_index_store import msn_manual_release_index_store_report_to_json, store_msn_manual_release_index


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build/store an MSN manual release index from explicit approved release JSON inputs.")
    parser.add_argument("--approved-release-json", required=True, help="Explicit MSN manual approved release package JSON file.")
    parser.add_argument("--output-dir", required=True, help="Directory where release index JSON files will be written.")
    parser.add_argument("--release-package-store-json", help="Optional approved release package store JSON file.")
    parser.add_argument("--index-label", default="operator_release_index")
    parser.add_argument("--print-index-json", action="store_true")
    return parser


def _read_json(path: str) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    release_store = _read_json(args.release_package_store_json) if args.release_package_store_json else None
    release_index = build_msn_manual_release_index(
        _read_json(args.approved_release_json),
        release_package_store_report=release_store,
        index_label=args.index_label,
    )
    store_report = store_msn_manual_release_index(release_index, args.output_dir)
    if args.print_index_json:
        sys.stdout.write(msn_manual_release_index_to_json(release_index))
    else:
        sys.stdout.write(msn_manual_release_index_store_report_to_json(store_report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
