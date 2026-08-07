from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from capture_msn_manual_article_extraction import extract_msn_manual_article
from capture_msn_manual_capture_bundle import build_msn_manual_capture_bundle
from capture_msn_manual_comments_extraction import extract_msn_manual_comments
from capture_msn_manual_total_export_manifest import build_msn_manual_total_export_packet, msn_manual_total_export_packet_to_json
from capture_msn_manual_total_export_package_store import msn_manual_total_export_package_store_result_to_json, store_msn_manual_total_export_package


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a review-ready Total Export package from explicit MSN manual capture artifacts.")
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--article-file", required=True, help="Explicit operator-supplied MSN article HTML/text artifact.")
    parser.add_argument("--comments-file", default="", help="Optional explicit operator-supplied MSN comments JSON/NDJSON/text artifact.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--package-id", default="msn_manual_total_export")
    parser.add_argument("--file-prefix", default="msn_manual_total_export")
    return parser


def _read_explicit_file(value: str) -> tuple[str, str]:
    path = Path(value)
    if not path.is_file():
        raise ValueError(f"explicit artifact file does not exist: {path.name}")
    return path.name, path.read_text(encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        article_name, article_text = _read_explicit_file(args.article_file)
        article = extract_msn_manual_article(source_url=args.source_url, artifact_text=article_text, artifact_file_name=article_name)
        comments = None
        if args.comments_file:
            comments_name, comments_text = _read_explicit_file(args.comments_file)
            comments = extract_msn_manual_comments(source_url=args.source_url, artifact_text=comments_text, artifact_file_name=comments_name)
        bundle = build_msn_manual_capture_bundle(article=article, comments=comments)
        packet = build_msn_manual_total_export_packet(bundle=bundle, package_id=args.package_id)
        store_result = store_msn_manual_total_export_package(output_dir=Path(args.output_dir), bundle=bundle, package_id=args.package_id, file_prefix=args.file_prefix)
        print(
            json.dumps(
                {
                    "packet": json.loads(msn_manual_total_export_packet_to_json(packet)),
                    "store_result": json.loads(msn_manual_total_export_package_store_result_to_json(store_result)),
                },
                sort_keys=True,
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    except Exception as exc:  # pragma: no cover - exercised by subprocess tests
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
