from __future__ import annotations

import argparse
import sys
from typing import Sequence

from preservation_evidence_bundle import (
    BUNDLE_STATUSES,
    REPORT_FORMATS,
    build_preservation_evidence_bundle,
    build_preservation_evidence_item,
    render_preservation_evidence_bundle,
)


def _parse_item(value: str):
    parts = [part.strip() for part in str(value or "").split(":")]
    if len(parts) not in (2, 3) or not parts[0] or not parts[1]:
        raise ValueError(
            "item must use artifact_id:artifact_format[:capture_method_id]"
        )
    return build_preservation_evidence_item(
        artifact_id=parts[0],
        artifact_format=parts[1],
        capture_method_id=parts[2] if len(parts) == 3 else "",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render local preservation evidence bundle metadata without touching evidence files.",
    )
    parser.add_argument("--source-url", default="")
    parser.add_argument("--source-id", default="")
    parser.add_argument("--source-name", default="")
    parser.add_argument("--bundle-label", default="")
    parser.add_argument("--status", choices=BUNDLE_STATUSES, default="planned")
    parser.add_argument(
        "--item",
        action="append",
        default=[],
        help="Repeatable artifact_id:artifact_format[:capture_method_id] metadata.",
    )
    parser.add_argument("--notes", default="")
    parser.add_argument("--format", choices=REPORT_FORMATS, default="text")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        items = tuple(_parse_item(value) for value in args.item)
        bundle = build_preservation_evidence_bundle(
            source_url=args.source_url,
            source_id=args.source_id,
            source_name=args.source_name,
            bundle_label=args.bundle_label,
            status=args.status,
            notes=args.notes,
            items=items,
        )
        print(render_preservation_evidence_bundle(bundle, output_format=args.format))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
