from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from total_export_bundle_index import (
    build_bundle_index,
    build_bundle_index_markdown,
    build_bundle_index_text,
    bundle_index_to_dict,
)


FORMAT_TEXT = "text"
FORMAT_MARKDOWN = "markdown"
FORMAT_JSON = "json"
OUTPUT_FORMATS = (FORMAT_TEXT, FORMAT_MARKDOWN, FORMAT_JSON)


def render_bundle_index(index, output_format: str) -> str:
    if output_format == FORMAT_MARKDOWN:
        return build_bundle_index_markdown(index)
    if output_format == FORMAT_JSON:
        return json.dumps(bundle_index_to_dict(index), indent=2, sort_keys=True)
    return build_bundle_index_text(index)


def write_output_file(output_path: str, text: str, *, overwrite: bool = False) -> str:
    path = Path(output_path)
    if path.exists() and not overwrite:
        raise ValueError(f"Output file already exists: {output_path}. Use --overwrite to replace it.")
    path.write_text(text, encoding="utf-8")
    return str(path)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a local-only Total Export bundle index from existing ZIP sidecars."
    )
    parser.add_argument("--root", required=True, help="Local folder containing bundle ZIP files.")
    parser.add_argument(
        "--format",
        choices=OUTPUT_FORMATS,
        default=FORMAT_TEXT,
        help="Output format: text, markdown, or json.",
    )
    parser.add_argument("--recursive", action="store_true", help="Scan nested folders for ZIP files.")
    parser.add_argument(
        "--no-compute-hash",
        action="store_true",
        help="Do not compute local ZIP SHA-256 values; sidecar hashes will be marked not compared.",
    )
    parser.add_argument("--output", default="", help="Optional output file path.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite an existing output file.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        index = build_bundle_index(
            args.root,
            recursive=args.recursive,
            compute_hash=not args.no_compute_hash,
        )
        rendered = render_bundle_index(index, args.format)
        if args.output:
            write_output_file(args.output, rendered, overwrite=args.overwrite)
        else:
            print(rendered)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
