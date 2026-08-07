from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from source_total_export_package import build_source_total_export_package, dump_json, load_json_file
from source_total_export_package_store import store_source_total_export_package


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a shared source Total Export package from an explicit capture bundle JSON.")
    parser.add_argument("--capture-bundle-json", required=True, help="Path to source capture bundle JSON.")
    parser.add_argument("--capture-manifest-json", help="Optional path to source capture manifest JSON.")
    parser.add_argument("--total-export-handoff-json", help="Optional path to source capture Total Export handoff JSON.")
    parser.add_argument("--export-profile", default="source_adapter_shared_v1", help="Deterministic export profile label.")
    parser.add_argument("--package-note", action="append", default=[], help="Optional package note; may be repeated.")
    parser.add_argument("--output-dir", required=True, help="Directory where output JSON files will be written.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    capture_bundle = load_json_file(args.capture_bundle_json)
    capture_manifest = load_json_file(args.capture_manifest_json) if args.capture_manifest_json else None
    total_export_handoff = load_json_file(args.total_export_handoff_json) if args.total_export_handoff_json else None
    outputs = build_source_total_export_package(
        capture_bundle=capture_bundle,
        capture_manifest=capture_manifest,
        total_export_handoff=total_export_handoff,
        export_profile=args.export_profile,
        package_notes=args.package_note,
    )
    receipt = store_source_total_export_package(outputs.as_dict(), Path(args.output_dir))
    print(dump_json(receipt), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
