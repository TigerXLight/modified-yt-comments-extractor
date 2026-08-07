from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from source_capture_bundle import build_source_capture_bundle, dump_json, load_json_file
from source_capture_bundle_store import store_source_capture_bundle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a shared source capture bundle from explicit extraction JSON inputs.")
    parser.add_argument("--content-extraction-json", required=True, help="Path to source content extraction JSON.")
    parser.add_argument("--comment-extraction-json", help="Optional path to source comment extraction JSON.")
    parser.add_argument("--artifact-collection-json", help="Optional path to source artifact collection JSON.")
    parser.add_argument("--adapter-id", help="Adapter id override.")
    parser.add_argument("--source-url", help="Source URL override.")
    parser.add_argument("--operator-note", action="append", default=[], help="Optional operator note; may be repeated.")
    parser.add_argument("--output-dir", required=True, help="Directory where output JSON files will be written.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    content = load_json_file(args.content_extraction_json)
    comments = load_json_file(args.comment_extraction_json) if args.comment_extraction_json else None
    collection = load_json_file(args.artifact_collection_json) if args.artifact_collection_json else None
    outputs = build_source_capture_bundle(
        content_extraction=content,
        comment_extraction=comments,
        artifact_collection=collection,
        adapter_id=args.adapter_id,
        source_url=args.source_url,
        operator_notes=args.operator_note,
    )
    receipt = store_source_capture_bundle(outputs.as_dict(), Path(args.output_dir))
    print(dump_json(receipt), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
