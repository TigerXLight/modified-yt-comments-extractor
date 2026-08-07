from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from source_release_index import build_source_release_index, dump_json, load_json_file
from source_release_index_store import store_source_release_index


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a shared source release-index record from an approved release package.")
    parser.add_argument("--approved-release-package-json", required=True, help="Path to source approved release package JSON.")
    parser.add_argument("--approved-release-manifest-json", help="Optional path to source approved release manifest JSON.")
    parser.add_argument("--release-index-handoff-json", help="Optional path to source approved release index handoff JSON.")
    parser.add_argument("--indexer-id", default="manual_indexer", help="Non-secret indexer/operator identifier.")
    parser.add_argument("--release-index-profile", default="source_adapter_shared_release_index_v1", help="Deterministic release index profile label.")
    parser.add_argument("--release-note", action="append", default=[], help="Optional release index note; may be repeated.")
    parser.add_argument("--output-dir", required=True, help="Directory where output JSON files will be written.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    outputs = build_source_release_index(
        approved_release_package=load_json_file(args.approved_release_package_json),
        approved_release_manifest=load_json_file(args.approved_release_manifest_json) if args.approved_release_manifest_json else None,
        release_index_handoff=load_json_file(args.release_index_handoff_json) if args.release_index_handoff_json else None,
        indexer_id=args.indexer_id,
        release_index_profile=args.release_index_profile,
        release_notes=args.release_note,
    )
    receipt = store_source_release_index(outputs.as_dict(), Path(args.output_dir))
    print(dump_json(receipt), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
