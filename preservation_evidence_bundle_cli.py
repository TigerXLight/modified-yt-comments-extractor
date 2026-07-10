# Evidence item spec parsing helper reuse.
# Evidence bundle CLI item detail flags.
from __future__ import annotations

import argparse
import sys
from typing import Sequence

from preservation_evidence_bundle import (
    BUNDLE_STATUSES,
    REPORT_FORMATS,
    build_preservation_evidence_bundle,
    build_preservation_evidence_items_from_specs,
    render_preservation_evidence_bundle,
)


def _parse_items_with_details(args) -> tuple:
    return build_preservation_evidence_items_from_specs(
        args.item,
        item_role_specs=args.item_role,
        item_origin_specs=args.item_origin,
        item_path_hint_specs=args.item_path_hint,
        item_note_specs=args.item_notes,
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
    parser.add_argument(
        "--item-role",
        action="append",
        default=[],
        help="Repeatable artifact_id=role metadata for an item.",
    )
    parser.add_argument(
        "--item-origin",
        action="append",
        default=[],
        help="Repeatable artifact_id=origin metadata for an item.",
    )
    parser.add_argument(
        "--item-path-hint",
        action="append",
        default=[],
        help="Repeatable artifact_id=path hint label. The path is not opened or checked.",
    )
    parser.add_argument(
        "--item-notes",
        action="append",
        default=[],
        help="Repeatable artifact_id=notes metadata for an item.",
    )
    parser.add_argument("--notes", default="")
    parser.add_argument("--format", choices=REPORT_FORMATS, default="text")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        items = _parse_items_with_details(args)
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
