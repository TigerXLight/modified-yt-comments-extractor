from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from source_adapter_capability_report import (
    REPORT_FORMATS,
    build_source_adapter_capability_report,
    render_source_adapter_capability_report,
)
from source_adapters import AVAILABLE_SOURCE_ADAPTERS, SourceAdapter, find_source_adapter_by_name


def _select_adapters(adapter_names: Sequence[str]) -> tuple[SourceAdapter, ...]:
    if not adapter_names:
        return tuple(AVAILABLE_SOURCE_ADAPTERS)

    selected: list[SourceAdapter] = []
    missing: list[str] = []
    seen: set[str] = set()

    for name in adapter_names:
        adapter = find_source_adapter_by_name(name)
        if adapter is None:
            missing.append(name)
            continue
        if adapter.source_name in seen:
            continue
        selected.append(adapter)
        seen.add(adapter.source_name)

    if missing:
        raise ValueError(f"unknown source adapter(s): {', '.join(missing)}")

    return tuple(selected)


def write_report_output(output_path: str, text: str, *, overwrite: bool = False) -> None:
    path = Path(output_path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"output path already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render local source adapter capability metadata without fetch/capture/network behavior.",
    )
    parser.add_argument(
        "--adapter",
        action="append",
        default=[],
        help="Optional source adapter id to include. Can be repeated.",
    )
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
        adapters = _select_adapters(args.adapter)
        report = build_source_adapter_capability_report(adapters=adapters)
        rendered = render_source_adapter_capability_report(
            report,
            output_format=args.format,
        )
        if args.output:
            write_report_output(args.output, rendered, overwrite=args.overwrite)
        else:
            print(rendered)
    except (OSError, ValueError, FileExistsError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
