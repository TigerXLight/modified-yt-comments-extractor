from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from preservation_evidence_bundle import (
    BUNDLE_STATUSES,
    REPORT_FORMATS,
    build_preservation_evidence_bundle,
    build_preservation_evidence_bundle_from_dict,
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

def _read_input_json(path: str) -> dict[str, Any]:
    input_path = Path(path)
    if not input_path.exists():
        raise FileNotFoundError(f"input file not found: {input_path}")
    try:
        data = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {input_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("input JSON must be an object")
    return data


def _disallow_input_overrides(args) -> None:
    if not args.input:
        return
    overridden = []
    if args.source_url:
        overridden.append("--source-url")
    if args.source_id:
        overridden.append("--source-id")
    if args.source_name:
        overridden.append("--source-name")
    if args.bundle_label:
        overridden.append("--bundle-label")
    if args.status != "planned":
        overridden.append("--status")
    if args.notes:
        overridden.append("--notes")
    if args.item:
        overridden.append("--item")
    if args.item_role:
        overridden.append("--item-role")
    if args.item_origin:
        overridden.append("--item-origin")
    if args.item_path_hint:
        overridden.append("--item-path-hint")
    if args.item_notes:
        overridden.append("--item-notes")
    if overridden:
        raise ValueError(
            "--input cannot be combined with bundle/item metadata flags: "
            + ", ".join(overridden)
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render local preservation evidence bundle metadata without touching evidence files.",
    )
    parser.add_argument(
        "--input",
        default="",
        help="Optional explicit local JSON bundle metadata file. This reads only the JSON file, not any path hints inside it.",
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
        if args.input:
            _disallow_input_overrides(args)
            bundle = build_preservation_evidence_bundle_from_dict(
                _read_input_json(args.input)
            )
        else:
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
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
