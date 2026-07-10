# Evidence bundle item detail flags integration.
# Evidence bundle integration: preservation backend CLI flags.
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from capture_method_metadata import available_capture_methods
from preservation_backend_plan import (
    REPORT_FORMATS,
    build_preservation_backend_plan,
    render_preservation_backend_plan,
)
from preservation_evidence_bundle import (
    BUNDLE_STATUSES,
    build_preservation_evidence_bundle,
    build_preservation_evidence_item,
)


def _read_input(path: str) -> dict[str, Any]:
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


def _optional_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key, "")
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value


def _optional_string_list(data: dict[str, Any], key: str) -> list[str]:
    value = data.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{key} must be a list of strings")
    return value


def _build_plan_from_input(
    data: dict[str, Any],
    *,
    capture_method_ids: Sequence[str] | None = None,
    evidence_bundle=None,
):
    return build_preservation_backend_plan(
        source_url=_optional_string(data, "source_url"),
        selected_backend_ids=_optional_string_list(data, "selected_backend_ids"),
        selected_format_ids=_optional_string_list(data, "selected_format_ids"),
        selected_capture_method_ids=(
            list(capture_method_ids)
            if capture_method_ids is not None
            else _optional_string_list(data, "selected_capture_method_ids")
        ),
        media_preservation_choice=_optional_string(
            data, "media_preservation_choice"
        ),
        notes=_optional_string(data, "notes"),
        evidence_bundle=evidence_bundle,
    )


def write_report_output(output_path: str, text: str, *, overwrite: bool = False) -> None:
    path = Path(output_path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"output path already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _parse_evidence_key_value_specs(values: Sequence[str], *, field_name: str) -> dict[str, str]:
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


def _validate_evidence_detail_ids(
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
            "evidence item detail metadata references unknown artifact IDs: "
            + ", ".join(sorted(unknown))
        )


def _parse_preservation_evidence_item(
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
            "evidence item must use artifact_id:artifact_format[:capture_method_id]"
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


def _build_cli_evidence_bundle(
    *,
    source_url: str = "",
    bundle_label: str = "",
    status: str = "",
    notes: str = "",
    item_values: Sequence[str] = (),
    item_role_values: Sequence[str] = (),
    item_origin_values: Sequence[str] = (),
    item_path_hint_values: Sequence[str] = (),
    item_note_values: Sequence[str] = (),
):
    if not (
        status
        or bundle_label
        or notes
        or item_values
        or item_role_values
        or item_origin_values
        or item_path_hint_values
        or item_note_values
    ):
        return None

    item_roles = _parse_evidence_key_value_specs(
        item_role_values,
        field_name="evidence item role",
    )
    item_origins = _parse_evidence_key_value_specs(
        item_origin_values,
        field_name="evidence item origin",
    )
    item_path_hints = _parse_evidence_key_value_specs(
        item_path_hint_values,
        field_name="evidence item path hint",
    )
    item_notes = _parse_evidence_key_value_specs(
        item_note_values,
        field_name="evidence item note",
    )

    artifact_ids = {
        str(value or "").split(":", 1)[0].strip()
        for value in item_values
        if str(value or "").split(":", 1)[0].strip()
    }
    _validate_evidence_detail_ids(
        artifact_ids=artifact_ids,
        detail_maps={
            "role": item_roles,
            "origin": item_origins,
            "path_hint": item_path_hints,
            "note": item_notes,
        },
    )

    items = tuple(
        _parse_preservation_evidence_item(
            value,
            item_roles=item_roles,
            item_origins=item_origins,
            item_path_hints=item_path_hints,
            item_notes=item_notes,
        )
        for value in item_values
    )
    return build_preservation_evidence_bundle(
        source_url=source_url or "",
        bundle_label=bundle_label or "",
        status=status or "planned",
        notes=notes or "",
        items=items,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a local preservation backend plan without fetch/capture/archive execution.",
    )
    parser.add_argument(
        "--input",
        default="",
        help="Optional JSON input path. Without input, renders available backend/format options with no selections.",
    )
    parser.add_argument(
        "--format",
        choices=REPORT_FORMATS,
        default="markdown",
        help="Output format.",
    )
    parser.add_argument("--output", default="", help="Optional output path.")
    parser.add_argument(
        "--capture-method",
        action="append",
        choices=tuple(
            method.method_id for method in available_capture_methods()
        ),
        default=None,
        help="Optional repeatable capture-method ID to include as planning metadata.",
    )
    parser.add_argument(
        "--evidence-bundle-status",
        choices=BUNDLE_STATUSES,
        default="",
        help="Optional metadata-only evidence bundle status.",
    )
    parser.add_argument(
        "--evidence-bundle-label",
        default="",
        help="Optional metadata-only evidence bundle label.",
    )
    parser.add_argument(
        "--evidence-item",
        action="append",
        default=[],
        help="Repeatable metadata-only artifact_id:artifact_format[:capture_method_id] evidence item.",
    )
    parser.add_argument(
        "--evidence-notes",
        default="",
        help="Optional metadata-only evidence bundle notes.",
    )
    parser.add_argument(
        "--evidence-item-role",
        action="append",
        default=[],
        help="Repeatable metadata-only artifact_id=role detail for an evidence item.",
    )
    parser.add_argument(
        "--evidence-item-origin",
        action="append",
        default=[],
        help="Repeatable metadata-only artifact_id=origin detail for an evidence item.",
    )
    parser.add_argument(
        "--evidence-item-path-hint",
        action="append",
        default=[],
        help="Repeatable metadata-only artifact_id=path hint label. The path is not opened or checked.",
    )
    parser.add_argument(
        "--evidence-item-notes",
        action="append",
        default=[],
        help="Repeatable metadata-only artifact_id=notes detail for an evidence item.",
    )
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
        data = _read_input(args.input) if args.input else {}
        evidence_bundle = _build_cli_evidence_bundle(
            source_url=_optional_string(data, "source_url") if data else "",
            bundle_label=args.evidence_bundle_label,
            status=args.evidence_bundle_status,
            notes=args.evidence_notes,
            item_values=args.evidence_item,
            item_role_values=args.evidence_item_role,
            item_origin_values=args.evidence_item_origin,
            item_path_hint_values=args.evidence_item_path_hint,
            item_note_values=args.evidence_item_notes,
        )
        plan = _build_plan_from_input(
            data,
            capture_method_ids=args.capture_method,
            evidence_bundle=evidence_bundle,
        )
        rendered = render_preservation_backend_plan(
            plan,
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
