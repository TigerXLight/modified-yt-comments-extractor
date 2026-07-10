# Evidence bundle CLI item detail flags.
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


def _parse_key_value_specs(values: Sequence[str], *, field_name: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for value in values:
        text = str(value or "").strip()
        if not text or "=" not in text:
            raise ValueError(f"{field_name} must use artifact_id=value")
        artifact_id, metadata_value = text.split("=", 1)
        normalized_id = artifact_id.strip()
        if not normalized_id:
            raise ValueError(f"{field_name} artifact_id must not be empty")
        if normalized_id in mapping:
            raise ValueError(f"duplicate {field_name} metadata for artifact ID: {normalized_id}")
        mapping[normalized_id] = metadata_value.strip()
    return mapping


def _validate_detail_ids(
    *,
    artifact_ids: set[str],
    detail_maps: dict[str, dict[str, str]],
) -> None:
    unknown: list[str] = []
    for field_name, mapping in detail_maps.items():
        for artifact_id in mapping:
            if artifact_id not in artifact_ids:
                unknown.append(f"{field_name}:{artifact_id}")
    if unknown:
        raise ValueError(
            "item detail metadata references unknown artifact IDs: "
            + ", ".join(sorted(unknown))
        )


def _parse_item(
    value: str,
    *,
    item_roles: dict[str, str] | None = None,
    item_origins: dict[str, str] | None = None,
    item_path_hints: dict[str, str] | None = None,
    item_notes: dict[str, str] | None = None,
):
    parts = [part.strip() for part in str(value or "").split(":")]
    if len(parts) not in (2, 3) or not parts[0] or not parts[1]:
        raise ValueError(
            "item must use artifact_id:artifact_format[:capture_method_id]"
        )
    artifact_id = parts[0]
    item_roles = item_roles or {}
    item_origins = item_origins or {}
    item_path_hints = item_path_hints or {}
    item_notes = item_notes or {}
    return build_preservation_evidence_item(
        artifact_id=artifact_id,
        artifact_format=parts[1],
        capture_method_id=parts[2] if len(parts) == 3 else "",
        artifact_role=item_roles.get(artifact_id, "supporting"),
        origin=item_origins.get(artifact_id, "unknown"),
        path_hint=item_path_hints.get(artifact_id, ""),
        notes=item_notes.get(artifact_id, ""),
    )


def _parse_items_with_details(args) -> tuple:
    item_roles = _parse_key_value_specs(
        args.item_role,
        field_name="item role",
    )
    item_origins = _parse_key_value_specs(
        args.item_origin,
        field_name="item origin",
    )
    item_path_hints = _parse_key_value_specs(
        args.item_path_hint,
        field_name="item path hint",
    )
    item_notes = _parse_key_value_specs(
        args.item_notes,
        field_name="item notes",
    )

    artifact_ids = {
        str(value or "").split(":", 1)[0].strip()
        for value in args.item
        if str(value or "").split(":", 1)[0].strip()
    }
    _validate_detail_ids(
        artifact_ids=artifact_ids,
        detail_maps={
            "role": item_roles,
            "origin": item_origins,
            "path_hint": item_path_hints,
            "notes": item_notes,
        },
    )

    return tuple(
        _parse_item(
            value,
            item_roles=item_roles,
            item_origins=item_origins,
            item_path_hints=item_path_hints,
            item_notes=item_notes,
        )
        for value in args.item
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
