from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Sequence

from capture_method_metadata import (
    capture_method_by_id,
    capture_method_metadata_to_dict,
)
from preservation_backend_plan import FORMAT_OPTIONS


REPORT_FORMATS = ("markdown", "text", "json")

BUNDLE_STATUS_PLANNED = "planned"
BUNDLE_STATUS_MANUAL_SUPPLIED = "manual_supplied"
BUNDLE_STATUS_EXTERNAL_OUTPUT = "external_output"
BUNDLE_STATUSES = (
    BUNDLE_STATUS_PLANNED,
    BUNDLE_STATUS_MANUAL_SUPPLIED,
    BUNDLE_STATUS_EXTERNAL_OUTPUT,
)

ARTIFACT_ROLES = ("primary", "supporting", "context", "media_asset", "metadata")
ARTIFACT_ORIGINS = ("manual", "external_tool", "future_backend", "unknown")

PRESERVATION_EVIDENCE_SCOPE = (
    "local descriptive metadata only; no file open, scan, validation, hashing, creation, "
    "upload, fetch, screenshot, DOM capture, scrolling, scraping, download, browser, "
    "ArchiveBox execution, network, credential, provider, or GUI behavior"
)


@dataclass(frozen=True)
class PreservationEvidenceItem:
    artifact_id: str
    artifact_format: str
    capture_method_id: str = ""
    artifact_role: str = "supporting"
    origin: str = "unknown"
    path_hint: str = ""
    notes: str = ""
    limitations: str = ""


@dataclass(frozen=True)
class PreservationEvidenceBundle:
    source_url: str = ""
    source_id: str = ""
    source_name: str = ""
    bundle_label: str = ""
    status: str = BUNDLE_STATUS_PLANNED
    notes: str = ""
    warnings: tuple[str, ...] = ()
    items: tuple[PreservationEvidenceItem, ...] = ()
    scope: str = PRESERVATION_EVIDENCE_SCOPE


def _normalize_catalog_value(
    value: str,
    *,
    field_name: str,
    allowed_values: Sequence[str],
) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in allowed_values:
        raise ValueError(
            f"invalid {field_name}: {normalized or '(empty)'}; "
            f"expected one of {', '.join(allowed_values)}"
        )
    return normalized


def available_artifact_formats() -> tuple[str, ...]:
    return tuple(option.format_id for option in FORMAT_OPTIONS)



def parse_evidence_item_detail_specs(
    values: Sequence[str],
    *,
    field_name: str,
) -> dict[str, str]:
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
            raise ValueError(
                f"duplicate {field_name} metadata for artifact ID: {normalized_id}"
            )
        mapping[normalized_id] = metadata_value.strip()
    return mapping


def _parse_evidence_item_spec(
    value: str,
) -> tuple[str, str, str]:
    parts = [part.strip() for part in str(value or "").split(":")]
    if len(parts) not in (2, 3) or not parts[0] or not parts[1]:
        raise ValueError(
            "item must use artifact_id:artifact_format[:capture_method_id]"
        )
    return parts[0], parts[1], parts[2] if len(parts) == 3 else ""


def build_preservation_evidence_items_from_specs(
    item_specs: Sequence[str],
    *,
    item_role_specs: Sequence[str] = (),
    item_origin_specs: Sequence[str] = (),
    item_path_hint_specs: Sequence[str] = (),
    item_note_specs: Sequence[str] = (),
) -> tuple[PreservationEvidenceItem, ...]:
    item_roles = parse_evidence_item_detail_specs(
        item_role_specs,
        field_name="item role",
    )
    item_origins = parse_evidence_item_detail_specs(
        item_origin_specs,
        field_name="item origin",
    )
    item_path_hints = parse_evidence_item_detail_specs(
        item_path_hint_specs,
        field_name="item path hint",
    )
    item_notes = parse_evidence_item_detail_specs(
        item_note_specs,
        field_name="item notes",
    )

    parsed_items = tuple(_parse_evidence_item_spec(value) for value in item_specs)
    artifact_ids = {artifact_id for artifact_id, _artifact_format, _capture_method_id in parsed_items}
    unknown_details: list[str] = []
    for field_name, mapping in (
        ("role", item_roles),
        ("origin", item_origins),
        ("path_hint", item_path_hints),
        ("notes", item_notes),
    ):
        for artifact_id in mapping:
            if artifact_id not in artifact_ids:
                unknown_details.append(f"{field_name}:{artifact_id}")
    if unknown_details:
        raise ValueError(
            "item detail metadata references unknown artifact IDs: "
            + ", ".join(sorted(unknown_details))
        )

    return tuple(
        build_preservation_evidence_item(
            artifact_id=artifact_id,
            artifact_format=artifact_format,
            capture_method_id=capture_method_id,
            artifact_role=item_roles.get(artifact_id, "supporting"),
            origin=item_origins.get(artifact_id, "unknown"),
            path_hint=item_path_hints.get(artifact_id, ""),
            notes=item_notes.get(artifact_id, ""),
        )
        for artifact_id, artifact_format, capture_method_id in parsed_items
    )


def build_preservation_evidence_item(
    *,
    artifact_id: str,
    artifact_format: str,
    capture_method_id: str = "",
    artifact_role: str = "supporting",
    origin: str = "unknown",
    path_hint: str = "",
    notes: str = "",
    limitations: str = "",
) -> PreservationEvidenceItem:
    normalized_id = str(artifact_id or "").strip()
    if not normalized_id:
        raise ValueError("artifact_id must not be empty")

    normalized_format = _normalize_catalog_value(
        artifact_format,
        field_name="artifact format",
        allowed_values=available_artifact_formats(),
    )
    normalized_role = _normalize_catalog_value(
        artifact_role,
        field_name="artifact role",
        allowed_values=ARTIFACT_ROLES,
    )
    normalized_origin = _normalize_catalog_value(
        origin,
        field_name="artifact origin",
        allowed_values=ARTIFACT_ORIGINS,
    )

    normalized_capture_method = str(capture_method_id or "").strip().lower()
    capture_method = None
    if normalized_capture_method:
        capture_method = capture_method_by_id(normalized_capture_method)
        if capture_method is None:
            raise ValueError(
                f"invalid capture method ID: {normalized_capture_method}"
            )

    limitation_parts = []
    if capture_method is not None:
        limitation_parts.append(capture_method.limitations)
    supplied_limitations = str(limitations or "").strip()
    if supplied_limitations:
        limitation_parts.append(supplied_limitations)

    return PreservationEvidenceItem(
        artifact_id=normalized_id,
        artifact_format=normalized_format,
        capture_method_id=normalized_capture_method,
        artifact_role=normalized_role,
        origin=normalized_origin,
        path_hint=str(path_hint or "").strip(),
        notes=str(notes or "").strip(),
        limitations=" ".join(limitation_parts),
    )


def build_preservation_evidence_bundle(
    *,
    source_url: str = "",
    source_id: str = "",
    source_name: str = "",
    bundle_label: str = "",
    status: str = BUNDLE_STATUS_PLANNED,
    notes: str = "",
    items: Sequence[PreservationEvidenceItem] = (),
) -> PreservationEvidenceBundle:
    normalized_status = _normalize_catalog_value(
        status,
        field_name="bundle status",
        allowed_values=BUNDLE_STATUSES,
    )
    item_tuple = tuple(items)
    seen_ids: set[str] = set()
    duplicate_ids: list[str] = []
    for item in item_tuple:
        if item.artifact_id in seen_ids and item.artifact_id not in duplicate_ids:
            duplicate_ids.append(item.artifact_id)
        seen_ids.add(item.artifact_id)
    if duplicate_ids:
        raise ValueError(f"duplicate artifact IDs: {', '.join(duplicate_ids)}")

    warnings: list[str] = []
    if not item_tuple:
        warnings.append(
            "No evidence items are described; this is an empty/planned metadata bundle."
        )

    return PreservationEvidenceBundle(
        source_url=str(source_url or "").strip(),
        source_id=str(source_id or "").strip(),
        source_name=str(source_name or "").strip(),
        bundle_label=str(bundle_label or "").strip(),
        status=normalized_status,
        notes=str(notes or "").strip(),
        warnings=tuple(warnings),
        items=item_tuple,
    )



def _string_from_mapping(
    data: dict[str, Any],
    key: str,
    *,
    required: bool = False,
) -> str:
    value = data.get(key, "")
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    normalized = value.strip()
    if required and not normalized:
        raise ValueError(f"{key} must not be empty")
    return normalized


def build_preservation_evidence_item_from_dict(
    data: dict[str, Any],
) -> PreservationEvidenceItem:
    if not isinstance(data, dict):
        raise ValueError("evidence bundle item must be an object")
    return build_preservation_evidence_item(
        artifact_id=_string_from_mapping(data, "artifact_id", required=True),
        artifact_format=_string_from_mapping(data, "artifact_format", required=True),
        capture_method_id=_string_from_mapping(data, "capture_method_id"),
        artifact_role=_string_from_mapping(data, "artifact_role") or "supporting",
        origin=_string_from_mapping(data, "origin") or "unknown",
        path_hint=_string_from_mapping(data, "path_hint"),
        notes=_string_from_mapping(data, "notes"),
        limitations=_string_from_mapping(data, "limitations"),
    )


def build_preservation_evidence_bundle_from_dict(
    data: dict[str, Any],
) -> PreservationEvidenceBundle:
    if not isinstance(data, dict):
        raise ValueError("evidence_bundle must be an object")

    items_value = data.get("items", [])
    if items_value is None:
        items_value = []
    if not isinstance(items_value, list):
        raise ValueError("evidence_bundle.items must be a list")

    return build_preservation_evidence_bundle(
        source_url=_string_from_mapping(data, "source_url"),
        source_id=_string_from_mapping(data, "source_id"),
        source_name=_string_from_mapping(data, "source_name"),
        bundle_label=_string_from_mapping(data, "bundle_label"),
        status=_string_from_mapping(data, "status") or BUNDLE_STATUS_PLANNED,
        notes=_string_from_mapping(data, "notes"),
        items=tuple(
            build_preservation_evidence_item_from_dict(item)
            for item in items_value
        ),
    )


def preservation_evidence_item_to_dict(
    item: PreservationEvidenceItem,
) -> dict[str, Any]:
    capture_method = capture_method_by_id(item.capture_method_id)
    return {
        "artifact_format": item.artifact_format,
        "artifact_id": item.artifact_id,
        "artifact_role": item.artifact_role,
        "capture_method": (
            capture_method_metadata_to_dict(capture_method)
            if capture_method is not None
            else None
        ),
        "capture_method_id": item.capture_method_id,
        "limitations": item.limitations,
        "notes": item.notes,
        "origin": item.origin,
        "path_hint": item.path_hint,
    }


def preservation_evidence_bundle_to_dict(
    bundle: PreservationEvidenceBundle,
) -> dict[str, Any]:
    return {
        "bundle_label": bundle.bundle_label,
        "items": [preservation_evidence_item_to_dict(item) for item in bundle.items],
        "notes": bundle.notes,
        "scope": bundle.scope,
        "source_id": bundle.source_id,
        "source_name": bundle.source_name,
        "source_url": bundle.source_url,
        "status": bundle.status,
        "warnings": list(bundle.warnings),
    }


def build_preservation_evidence_bundle_markdown(
    bundle: PreservationEvidenceBundle,
) -> str:
    lines = [
        "# Preservation Evidence Bundle Metadata",
        "",
        "Descriptive metadata only. Paths are hints and are not opened, scanned, hashed, validated, created, or uploaded. No capture, browser, archive, download, or network action is performed.",
        "",
        f"- Status: {bundle.status}",
        f"- Bundle label: {bundle.bundle_label or 'none'}",
        f"- Source URL: {bundle.source_url or 'none'}",
        f"- Source ID: {bundle.source_id or 'none'}",
        f"- Source name: {bundle.source_name or 'none'}",
        f"- Item count: {len(bundle.items)}",
    ]
    if bundle.notes:
        lines.append(f"- Notes: {bundle.notes}")
    if bundle.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in bundle.warnings)
    lines.extend(["", "## Evidence Items", ""])
    if not bundle.items:
        lines.append("No evidence items are described. This does not imply that files exist or that capture occurred.")
    for item in bundle.items:
        lines.extend(
            [
                f"### {item.artifact_id}",
                "",
                f"- Format: {item.artifact_format}",
                f"- Capture method: {item.capture_method_id or 'none specified'}",
                f"- Role: {item.artifact_role}",
                f"- Origin: {item.origin}",
                f"- Path hint: {item.path_hint or 'none'}",
                f"- Notes: {item.notes or 'none'}",
                f"- Limitations: {item.limitations or 'none recorded'}",
                "- Execution: metadata only; this item does not prove file existence, completeness, or capture execution.",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def build_preservation_evidence_bundle_text(
    bundle: PreservationEvidenceBundle,
) -> str:
    lines = [
        "Preservation evidence bundle metadata",
        "Scope: local descriptive metadata only; no file open/scan/hash/validation/creation/upload or capture/network/browser/archive/download behavior.",
        f"status: {bundle.status}",
        f"bundle_label: {bundle.bundle_label or 'none'}",
        f"source_url: {bundle.source_url or 'none'}",
        f"source_id: {bundle.source_id or 'none'}",
        f"source_name: {bundle.source_name or 'none'}",
        f"item_count: {len(bundle.items)}",
    ]
    if bundle.notes:
        lines.append(f"notes: {bundle.notes}")
    if bundle.warnings:
        lines.append(f"warnings: {'; '.join(bundle.warnings)}")
    lines.append("items:")
    if not bundle.items:
        lines.append("- none; no file existence or capture execution is implied")
    for item in bundle.items:
        lines.append(
            f"- {item.artifact_id}: format={item.artifact_format}; "
            f"capture_method={item.capture_method_id or 'none'}; role={item.artifact_role}; "
            f"origin={item.origin}; path_hint={item.path_hint or 'none'}; "
            f"notes={item.notes or 'none'}; "
            f"limitations={item.limitations or 'none recorded'}; execution=metadata only"
        )
    return "\n".join(lines)


def render_preservation_evidence_bundle(
    bundle: PreservationEvidenceBundle,
    *,
    output_format: str,
) -> str:
    if output_format == "markdown":
        return build_preservation_evidence_bundle_markdown(bundle)
    if output_format == "text":
        return build_preservation_evidence_bundle_text(bundle)
    if output_format == "json":
        return json.dumps(
            preservation_evidence_bundle_to_dict(bundle),
            indent=2,
            sort_keys=True,
        )
    raise ValueError(f"unsupported output format: {output_format}")
