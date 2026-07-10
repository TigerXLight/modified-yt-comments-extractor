from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from total_export_local_media import build_local_media_record
from total_export_manual_archive import build_manual_archive_record
from total_export_preservation_plan import (
    build_preservation_plan,
    build_preservation_plan_markdown,
    build_preservation_plan_text,
    preservation_plan_to_dict,
)


FORMAT_TEXT = "text"
FORMAT_MARKDOWN = "markdown"
FORMAT_JSON = "json"
OUTPUT_FORMATS = (FORMAT_TEXT, FORMAT_MARKDOWN, FORMAT_JSON)


def _as_list(value: object, field_name: str) -> list[object]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    raise ValueError(f"{field_name} must be a list.")


def _as_dict(value: object, field_name: str) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    raise ValueError(f"{field_name} entries must be objects.")


def _clean_string(value: object) -> str:
    return str(value or "").strip()


def _load_input_json(input_path: str) -> dict[str, object]:
    path = Path(input_path)
    if not path.is_file():
        raise ValueError(f"Input file does not exist: {input_path}")
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON input: {exc}") from exc

    if isinstance(data, list):
        return {"source_urls": data}
    if isinstance(data, dict):
        return data
    raise ValueError("Input JSON must be an object or a list of source URLs.")


def _build_manual_archive_records(data: object):
    records = []
    for entry in _as_list(data, "manual_archive_records"):
        record = _as_dict(entry, "manual_archive_records")
        records.append(
            build_manual_archive_record(
                source_url=_clean_string(record.get("source_url")),
                normalized_url=_clean_string(record.get("normalized_url")),
                archive_url=_clean_string(record.get("archive_url")),
                archive_service_name=_clean_string(record.get("archive_service_name")),
                archive_capture_time=_clean_string(record.get("archive_capture_time")),
                archive_status=_clean_string(record.get("archive_status")),
                archive_notes=_clean_string(record.get("archive_notes")),
                entered_at_utc=_clean_string(record.get("entered_at_utc")),
                verified_by_user_at_utc=_clean_string(record.get("verified_by_user_at_utc")),
            )
        )
    return tuple(records)


def _optional_bool(value: object):
    if value is None or value == "":
        return None
    return bool(value)


def _build_local_media_records(data: object):
    records = []
    for entry in _as_list(data, "local_media_records"):
        record = _as_dict(entry, "local_media_records")
        records.append(
            build_local_media_record(
                source_url=_clean_string(record.get("source_url")),
                normalized_url=_clean_string(record.get("normalized_url")),
                package_id=_clean_string(record.get("package_id")),
                local_media_path=_clean_string(record.get("local_media_path")),
                local_media_filename=_clean_string(record.get("local_media_filename")),
                local_file_size_bytes=int(record.get("local_file_size_bytes") or 0),
                local_file_sha256=_clean_string(record.get("local_file_sha256")),
                media_type=_clean_string(record.get("media_type")),
                duration_seconds=record.get("duration_seconds"),
                media_notes=_clean_string(record.get("media_notes")),
                registered_at_utc=_clean_string(record.get("registered_at_utc")),
                verified_at_utc=_clean_string(record.get("verified_at_utc")),
                exists_at_registration=_optional_bool(record.get("exists_at_registration")),
                hash_algorithm=_clean_string(record.get("hash_algorithm")),
                status=_clean_string(record.get("status")),
                compute_hash=False,
                inspect_local_file=False,
            )
        )
    return tuple(records)


def build_plan_from_input_data(data: dict[str, object]):
    source_urls = tuple(_clean_string(value) for value in _as_list(data.get("source_urls"), "source_urls"))
    manual_archive_records = _build_manual_archive_records(data.get("manual_archive_records"))
    local_media_records = _build_local_media_records(data.get("local_media_records"))
    return build_preservation_plan(
        source_urls=source_urls,
        manual_archive_records=manual_archive_records,
        local_media_records=local_media_records,
    )


def render_preservation_plan(plan, output_format: str) -> str:
    if output_format == FORMAT_MARKDOWN:
        return build_preservation_plan_markdown(plan)
    if output_format == FORMAT_JSON:
        return json.dumps(preservation_plan_to_dict(plan), indent=2, sort_keys=True)
    return build_preservation_plan_text(plan)


def write_output_file(output_path: str, text: str, *, overwrite: bool = False) -> str:
    path = Path(output_path)
    if path.exists() and not overwrite:
        raise ValueError(f"Output file already exists: {output_path}. Use --overwrite to replace it.")
    path.write_text(text, encoding="utf-8")
    return str(path)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a local-only preservation plan from user-supplied JSON metadata."
    )
    parser.add_argument("--input", required=True, help="Path to local preservation plan JSON input.")
    parser.add_argument(
        "--format",
        choices=OUTPUT_FORMATS,
        default=FORMAT_TEXT,
        help="Output format: text, markdown, or json.",
    )
    parser.add_argument("--output", default="", help="Optional output file path.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite an existing output file.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        input_data = _load_input_json(args.input)
        plan = build_plan_from_input_data(input_data)
        rendered = render_preservation_plan(plan, args.format)
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
