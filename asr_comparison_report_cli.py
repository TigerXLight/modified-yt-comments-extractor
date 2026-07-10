from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from asr_comparison_report import (
    ASR_COMPARISON_METRICS,
    asr_comparison_records_to_dict,
    build_asr_comparison_markdown,
    build_asr_comparison_records_from_dicts,
    build_asr_comparison_text,
    rank_asr_records,
)


REPORT_FORMATS = ("text", "markdown", "json")


def load_asr_records_from_json(path: str) -> tuple[dict[str, Any], tuple]:
    input_path = Path(path)
    with input_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    metadata: dict[str, Any] = {}
    if isinstance(data, dict):
        raw_records = data.get("records")
        metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    elif isinstance(data, list):
        raw_records = data
    else:
        raise ValueError("input JSON must be an object with a records list or a bare records list")

    if not isinstance(raw_records, list):
        raise ValueError("input JSON must contain a records list")
    if not raw_records:
        raise ValueError("input JSON contains no records")
    if not all(isinstance(row, dict) for row in raw_records):
        raise ValueError("each ASR comparison record must be a JSON object")

    return metadata, build_asr_comparison_records_from_dicts(raw_records)


def render_asr_report(records: Sequence, *, output_format: str, metric: str) -> str:
    ranked = rank_asr_records(records, metric=metric)
    if output_format == "text":
        return build_asr_comparison_text(records, metric=metric)
    if output_format == "markdown":
        return build_asr_comparison_markdown(records, metric=metric)
    if output_format == "json":
        return json.dumps(
            asr_comparison_records_to_dict(ranked),
            indent=2,
            sort_keys=True,
        )
    raise ValueError(f"unsupported output format: {output_format}")


def write_report_output(output_path: str, text: str, *, overwrite: bool = False) -> None:
    path = Path(output_path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"output path already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render local/manual ASR comparison records without provider calls.",
    )
    parser.add_argument("--input", required=True, help="Path to ASR comparison JSON records.")
    parser.add_argument(
        "--format",
        choices=REPORT_FORMATS,
        default="text",
        help="Output format.",
    )
    parser.add_argument(
        "--metric",
        choices=ASR_COMPARISON_METRICS,
        default="reference_accuracy_percent",
        help="Ranking metric.",
    )
    parser.add_argument("--output", default="", help="Optional output path.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing an existing output file.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        _metadata, records = load_asr_records_from_json(args.input)
        rendered = render_asr_report(records, output_format=args.format, metric=args.metric)
        if args.output:
            write_report_output(args.output, rendered, overwrite=args.overwrite)
        else:
            print(rendered)
    except FileNotFoundError as exc:
        print(f"error: input file not found: {exc.filename}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON in {args.input}: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError, FileExistsError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
