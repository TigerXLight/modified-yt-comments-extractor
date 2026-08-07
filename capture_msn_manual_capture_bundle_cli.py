from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from capture_msn_manual_article_extraction import extract_msn_manual_article
from capture_msn_manual_capture_bundle import build_msn_manual_capture_bundle, msn_manual_capture_bundle_to_json
from capture_msn_manual_capture_bundle_store import msn_manual_capture_bundle_store_result_to_json, store_msn_manual_capture_bundle
from capture_msn_manual_comments_extraction import extract_msn_manual_comments


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a Total Export-ready MSN manual capture bundle from explicit operator artifacts.")
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--article-file", required=True, help="Explicit saved article text/html file.")
    parser.add_argument("--comments-file", default="", help="Optional explicit comments JSON/NDJSON/transcript file.")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--file-prefix", default="msn_manual_capture_bundle")
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
        response = {"bundle": json.loads(msn_manual_capture_bundle_to_json(bundle))}
        if args.output_dir:
            result = store_msn_manual_capture_bundle(output_dir=Path(args.output_dir), bundle=bundle, file_prefix=args.file_prefix)
            response["store_result"] = json.loads(msn_manual_capture_bundle_store_result_to_json(result))
        print(json.dumps(response, sort_keys=True, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:  # pragma: no cover - exercised by CLI process failures
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
