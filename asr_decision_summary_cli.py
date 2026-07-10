from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from asr_comparison_report_cli import load_asr_records_from_json
from asr_decision_summary import (
    asr_decision_summary_to_dict,
    build_asr_decision_summary,
    build_asr_decision_summary_markdown,
    build_asr_decision_summary_text,
)


REPORT_FORMATS = ("markdown", "text", "json")


def render_asr_decision_summary(records: Sequence, *, output_format: str) -> str:
    result = build_asr_decision_summary(records)
    if output_format == "markdown":
        return build_asr_decision_summary_markdown(result)
    if output_format == "text":
        return build_asr_decision_summary_text(result)
    if output_format == "json":
        return json.dumps(
            asr_decision_summary_to_dict(result),
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
        description="Render local/manual ASR decision summary records without provider calls.",
    )
    parser.add_argument("--input", required=True, help="Path to ASR comparison JSON records.")
    parser.add_argument(
        "--format",
        choices=REPORT_FORMATS,
        default="markdown",
        help="Output format.",
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
        rendered = render_asr_decision_summary(records, output_format=args.format)
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
