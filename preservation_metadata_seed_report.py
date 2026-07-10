from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from total_export_preservation_plan import (
    PreservationPlanResult,
    build_preservation_plan_markdown,
    build_preservation_plan_text,
    preservation_plan_to_dict,
)
from total_export_preservation_plan_cli import build_plan_from_input_data


DEFAULT_SEED_PATH = "PRESERVATION_METADATA_SEED.json"
FORMAT_MARKDOWN = "markdown"
FORMAT_TEXT = "text"
FORMAT_JSON = "json"
OUTPUT_FORMATS = (FORMAT_MARKDOWN, FORMAT_TEXT, FORMAT_JSON)

LOCAL_ONLY_WARNING = (
    "Seed paths, hashes, and URLs are example local metadata only and are not external verification."
)
HARD_BOUNDARY_WARNING = (
    "No archive checks, downloads, network/API calls, scraping, screenshots, transcription, "
    "provider calls, ZIP extraction, or GUI integration are performed."
)


@dataclass(frozen=True)
class PreservationMetadataSeedReportResult:
    seed_path: str
    source_count: int
    manual_archive_record_count: int
    local_media_record_count: int
    preservation_plan: PreservationPlanResult
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


def _as_list(value: object, field_name: str) -> list[object]:
    if isinstance(value, list):
        return value
    raise ValueError(f"Seed field {field_name} must be a list.")


def load_preservation_metadata_seed(input_path: str) -> dict[str, object]:
    path = Path(input_path)
    if not path.is_file():
        raise ValueError(f"Seed input file does not exist: {input_path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid seed JSON input: {exc}") from exc
    except OSError as exc:
        raise ValueError(f"Seed input could not be read: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Seed JSON input must be an object.")
    return data


def build_preservation_metadata_seed_report(
    input_path: str = DEFAULT_SEED_PATH,
) -> PreservationMetadataSeedReportResult:
    data = load_preservation_metadata_seed(input_path)
    source_urls = _as_list(data.get("source_urls"), "source_urls")
    archive_records = _as_list(data.get("manual_archive_records"), "manual_archive_records")
    media_records = _as_list(data.get("local_media_records"), "local_media_records")
    plan = build_plan_from_input_data(data)
    return PreservationMetadataSeedReportResult(
        seed_path=input_path,
        source_count=len(source_urls),
        manual_archive_record_count=len(archive_records),
        local_media_record_count=len(media_records),
        preservation_plan=plan,
        warnings=tuple(dict.fromkeys((*plan.warnings, LOCAL_ONLY_WARNING, HARD_BOUNDARY_WARNING))),
        errors=tuple(plan.errors),
    )


def preservation_metadata_seed_report_to_dict(
    result: PreservationMetadataSeedReportResult,
) -> dict[str, object]:
    return {
        "errors": list(result.errors),
        "local_media_record_count": result.local_media_record_count,
        "manual_archive_record_count": result.manual_archive_record_count,
        "preservation_plan": preservation_plan_to_dict(result.preservation_plan),
        "seed_path": result.seed_path,
        "source_count": result.source_count,
        "warnings": list(result.warnings),
    }


def build_preservation_metadata_seed_report_markdown(
    result: PreservationMetadataSeedReportResult,
) -> str:
    plan_lines = build_preservation_plan_markdown(result.preservation_plan).splitlines()
    if plan_lines and plan_lines[0].startswith("# "):
        plan_lines = plan_lines[2:]
    lines = [
        "# Preservation Metadata Seed Report",
        "",
        "Local-only deterministic report for the checked-in preservation metadata seed.",
        "",
        "## Seed Counts",
        "",
        f"- Seed file: `{result.seed_path}`",
        f"- Source count: {result.source_count}",
        f"- Manual archive record count: {result.manual_archive_record_count}",
        f"- Local media record count: {result.local_media_record_count}",
        f"- Sources needing follow-up: {result.preservation_plan.sources_needing_follow_up_count}",
        "",
        "## Preservation Plan",
        "",
        *plan_lines,
        "",
        "## Seed Safety Notes",
        "",
        *[f"- {warning}" for warning in result.warnings],
    ]
    if result.errors:
        lines.extend(["", "## Errors", "", *[f"- {error}" for error in result.errors]])
    return "\n".join(lines)


def build_preservation_metadata_seed_report_text(
    result: PreservationMetadataSeedReportResult,
) -> str:
    lines = [
        "Preservation metadata seed report",
        f"Seed file: {result.seed_path}",
        f"Source count: {result.source_count}",
        f"Manual archive record count: {result.manual_archive_record_count}",
        f"Local media record count: {result.local_media_record_count}",
        "",
        build_preservation_plan_text(result.preservation_plan),
        "",
        "Seed warnings:",
        *[f"- {warning}" for warning in result.warnings],
    ]
    if result.errors:
        lines.extend(["Errors:", *[f"- {error}" for error in result.errors]])
    return "\n".join(lines)


def render_preservation_metadata_seed_report(
    result: PreservationMetadataSeedReportResult,
    output_format: str,
) -> str:
    if output_format == FORMAT_TEXT:
        return build_preservation_metadata_seed_report_text(result)
    if output_format == FORMAT_JSON:
        return json.dumps(
            preservation_metadata_seed_report_to_dict(result),
            indent=2,
            sort_keys=True,
        )
    return build_preservation_metadata_seed_report_markdown(result)


def write_output_file(output_path: str, text: str, *, overwrite: bool = False) -> str:
    path = Path(output_path)
    if path.exists() and not overwrite:
        raise ValueError(f"Output file already exists: {output_path}. Use --overwrite to replace it.")
    path.write_text(text, encoding="utf-8")
    return str(path)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a local-only preservation metadata seed report."
    )
    parser.add_argument(
        "--input",
        default=DEFAULT_SEED_PATH,
        help=f"Local seed JSON path (default: {DEFAULT_SEED_PATH}).",
    )
    parser.add_argument(
        "--format",
        choices=OUTPUT_FORMATS,
        default=FORMAT_MARKDOWN,
        help="Output format: markdown, text, or json.",
    )
    parser.add_argument("--output", default="", help="Optional output file path.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite an existing output file.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        result = build_preservation_metadata_seed_report(args.input)
        rendered = render_preservation_metadata_seed_report(result, args.format)
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
