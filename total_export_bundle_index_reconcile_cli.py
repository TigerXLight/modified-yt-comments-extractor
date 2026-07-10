from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from total_export_bundle_index import build_bundle_index
from total_export_bundle_index_reconcile import (
    ExpectedBundleEntry,
    build_bundle_index_reconciliation_markdown,
    build_bundle_index_reconciliation_text,
    bundle_index_reconciliation_to_dict,
    reconcile_bundle_index,
)


FORMAT_TEXT = "text"
FORMAT_MARKDOWN = "markdown"
FORMAT_JSON = "json"
OUTPUT_FORMATS = (FORMAT_TEXT, FORMAT_MARKDOWN, FORMAT_JSON)


def _clean_string(value: object) -> str:
    return str(value or "").strip()


def _expected_entry(value: object) -> ExpectedBundleEntry:
    if isinstance(value, str):
        expected_path = value.strip()
        if not expected_path:
            raise ValueError("Expected bundle paths must not be empty.")
        return ExpectedBundleEntry(expected_zip_path=expected_path)
    if not isinstance(value, dict):
        raise ValueError("Expected bundle entries must be path strings or objects.")

    expected_path = _clean_string(value.get("expected_zip_path"))
    if not expected_path:
        raise ValueError("Expected bundle objects require expected_zip_path.")
    return ExpectedBundleEntry(
        expected_zip_path=expected_path,
        package_id=_clean_string(value.get("package_id")),
        source_url=_clean_string(value.get("source_url")),
        notes=_clean_string(value.get("notes")),
    )


def expected_bundle_entries_from_json_data(
    data: object,
) -> tuple[ExpectedBundleEntry, ...]:
    if isinstance(data, list):
        values = data
    elif isinstance(data, dict):
        values = data.get("expected_bundles")
        if not isinstance(values, list):
            raise ValueError("Input JSON must contain an expected_bundles list.")
    else:
        raise ValueError(
            "Input JSON must be an expected_bundles object or a list of expected entries."
        )
    return tuple(_expected_entry(value) for value in values)


def expected_bundle_entries_from_text(text: str) -> tuple[ExpectedBundleEntry, ...]:
    return tuple(
        ExpectedBundleEntry(expected_zip_path=line)
        for raw_line in text.splitlines()
        if (line := raw_line.strip()) and not line.startswith("#")
    )


def load_expected_bundle_entries(path: str) -> tuple[ExpectedBundleEntry, ...]:
    input_path = Path(path)
    if not input_path.is_file():
        raise ValueError(f"Expected bundle input file does not exist: {path}")
    try:
        text = input_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Expected bundle input could not be read: {exc}") from exc

    if input_path.suffix.lower() == ".json":
        try:
            return expected_bundle_entries_from_json_data(json.loads(text))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid expected bundle JSON: {exc}") from exc
    return expected_bundle_entries_from_text(text)


def render_bundle_index_reconciliation(result, output_format: str) -> str:
    if output_format == FORMAT_MARKDOWN:
        return build_bundle_index_reconciliation_markdown(result)
    if output_format == FORMAT_JSON:
        return json.dumps(
            bundle_index_reconciliation_to_dict(result),
            indent=2,
            sort_keys=True,
        )
    return build_bundle_index_reconciliation_text(result)


def write_output_file(output_path: str, text: str, *, overwrite: bool = False) -> str:
    path = Path(output_path)
    if path.exists() and not overwrite:
        raise ValueError(f"Output file already exists: {output_path}. Use --overwrite to replace it.")
    path.write_text(text, encoding="utf-8")
    return str(path)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Reconcile a local expected bundle list with an existing-folder Total Export bundle index."
        )
    )
    parser.add_argument("--root", required=True, help="Local folder containing bundle ZIP files.")
    parser.add_argument(
        "--expected",
        required=True,
        help="Local JSON or text file listing expected bundle ZIP paths.",
    )
    parser.add_argument(
        "--format",
        choices=OUTPUT_FORMATS,
        default=FORMAT_TEXT,
        help="Output format: text, markdown, or json.",
    )
    parser.add_argument("--recursive", action="store_true", help="Index nested folders for ZIP files.")
    parser.add_argument(
        "--no-compute-hash",
        action="store_true",
        help="Do not compute local ZIP SHA-256 values; sidecar comparison will need review.",
    )
    parser.add_argument("--output", default="", help="Optional output file path.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite an existing output file.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        expected_entries = load_expected_bundle_entries(args.expected)
        index = build_bundle_index(
            args.root,
            recursive=args.recursive,
            compute_hash=not args.no_compute_hash,
        )
        result = reconcile_bundle_index(expected_entries, index)
        rendered = render_bundle_index_reconciliation(result, args.format)
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
