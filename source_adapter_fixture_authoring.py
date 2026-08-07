from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "source_adapter_fixture_authoring_v1"
PACKAGE_SCHEMA_VERSION = "source_adapter_fixture_authoring_package_v1"
TEMPLATE_INDEX_SCHEMA_VERSION = "source_adapter_fixture_template_index_v1"
ROUTE_PLAN_SCHEMA_VERSION = "source_adapter_fixture_route_plan_v1"
REVIEW_HANDOFF_SCHEMA_VERSION = "source_adapter_fixture_review_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_fixture_authoring_operator_summary_v1"

_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
_FORBIDDEN_PATH_FIELDS = {"path", "absolute_path", "local_path", "filesystem_path"}

_TEMPLATE_JSON_BY_TYPE: dict[str, dict[str, Any]] = {
    "saved_article_html_or_text": {
        "artifact_role": "article_html_or_text",
        "operator_supplied_file_required": True,
        "notes": "Save the article HTML, readable text, or DOM text as an explicit local artifact.",
    },
    "saved_video_page_html_or_text": {
        "artifact_role": "article_html_or_text",
        "operator_supplied_file_required": True,
        "notes": "Save the video page HTML, readable text, transcript page text, or DOM text as an explicit artifact.",
    },
    "saved_document_text_or_html": {
        "artifact_role": "article_html_or_text",
        "operator_supplied_file_required": True,
        "notes": "Save extracted document text or source HTML as an explicit local artifact.",
    },
    "saved_local_artifact_text_or_html": {
        "artifact_role": "article_html_or_text",
        "operator_supplied_file_required": True,
        "notes": "Register a user-supplied local source artifact by safe basename and hash.",
    },
    "saved_comments_json_or_text": {
        "artifact_role": "comments_json_or_text",
        "operator_supplied_file_required": True,
        "notes": "Save comments, replies, or live chat as JSON, NDJSON, transcript text, or copied text.",
    },
    "expected_content_extraction_json": {
        "artifact_role": "expected_content_extraction_json",
        "operator_supplied_file_required": False,
        "notes": "Expected normalized content extraction assertions for the saved source fixture.",
    },
    "expected_comment_extraction_json": {
        "artifact_role": "expected_comment_extraction_json",
        "operator_supplied_file_required": False,
        "notes": "Expected normalized comment extraction assertions for the saved comment fixture.",
    },
    "expected_total_export_package_json": {
        "artifact_role": "expected_total_export_package_json",
        "operator_supplied_file_required": False,
        "notes": "Expected Total Export package assertions after shared-stage processing.",
    },
    "expected_review_release_archive_json": {
        "artifact_role": "expected_review_release_archive_json",
        "operator_supplied_file_required": False,
        "notes": "Expected Evidence Review, release, archive, and traceability assertions.",
    },
    "expected_pipeline_closeout_json": {
        "artifact_role": "expected_pipeline_closeout_json",
        "operator_supplied_file_required": False,
        "notes": "Expected final pipeline closeout assertions for this adapter fixture.",
    },
}


class SourceAdapterFixtureAuthoringError(ValueError):
    """Raised when fixture-authoring input is invalid."""


def _json_bytes(data: Mapping[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"


def _stable_hash(data: Mapping[str, Any], *, length: int = 12) -> str:
    return hashlib.sha256(_json_bytes(data)).hexdigest()[:length]


def _clean_identifier(value: object, *, fallback: str) -> str:
    text = str(value or "").strip() or fallback
    text = _SAFE_ID_RE.sub(".", text).strip("._-")
    return text or fallback


def _coerce_mapping(value: object, *, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise SourceAdapterFixtureAuthoringError(f"{name} must be a JSON object")
    return dict(value)


def _coerce_sequence(value: object, *, name: str) -> list[Any]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise SourceAdapterFixtureAuthoringError(f"{name} must be a JSON array")
    return list(value)


def _ensure_no_local_paths(value: Mapping[str, Any], *, name: str) -> None:
    present = sorted(_FORBIDDEN_PATH_FIELDS.intersection(value.keys()))
    if present:
        raise SourceAdapterFixtureAuthoringError(f"{name} must not include local path fields: {', '.join(present)}")


def _assert_no_forbidden_keys(value: object, *, name: str) -> None:
    if isinstance(value, Mapping):
        _ensure_no_local_paths(value, name=name)
        for key, child in value.items():
            _assert_no_forbidden_keys(child, name=f"{name}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _assert_no_forbidden_keys(child, name=f"{name}[{index}]")


def _text_list(value: object, *, name: str) -> list[str]:
    if value is None:
        return []
    items = _coerce_sequence(value, name=name)
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item or "").strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _load_rows(matrix: Mapping[str, Any]) -> list[dict[str, Any]]:
    fixture_matrix = _coerce_mapping(matrix.get("fixture_matrix", {}), name="fixture_matrix")
    rows = _coerce_sequence(fixture_matrix.get("rows", []), name="fixture_matrix.rows")
    normalized: list[dict[str, Any]] = []
    for index, raw_row in enumerate(rows):
        row = _coerce_mapping(raw_row, name=f"fixture_matrix.rows[{index}]")
        _ensure_no_local_paths(row, name=f"fixture_matrix.rows[{index}]")
        adapter_id = _clean_identifier(row.get("adapter_id"), fallback=f"adapter_{index + 1}").lower()
        fixture_types = [_clean_identifier(item, fallback="fixture").lower() for item in _text_list(row.get("fixture_types"), name="fixture_types")]
        if not fixture_types:
            raise SourceAdapterFixtureAuthoringError(f"adapter {adapter_id} has no fixture types")
        shared_pipeline_stages = [_clean_identifier(item, fallback="stage").lower() for item in _text_list(row.get("shared_pipeline_stages"), name="shared_pipeline_stages")]
        if not shared_pipeline_stages:
            raise SourceAdapterFixtureAuthoringError(f"adapter {adapter_id} has no shared pipeline stages")
        normalized.append(
            {
                "adapter_id": adapter_id,
                "display_name": str(row.get("display_name") or adapter_id).strip(),
                "source_kind": str(row.get("source_kind") or "web").strip().lower(),
                "coverage_status": str(row.get("coverage_status") or "READY_FOR_FIXTURE_AUTHORING").strip(),
                "fixture_types": fixture_types,
                "artifact_roles": _text_list(row.get("artifact_roles"), name="artifact_roles"),
                "adapter_specific_module_required": bool(row.get("adapter_specific_module_required", False)),
                "shared_pipeline_stages": shared_pipeline_stages,
            }
        )
    if not normalized:
        raise SourceAdapterFixtureAuthoringError("fixture matrix must contain at least one row")
    return normalized


def _selected_rows(rows: Sequence[Mapping[str, Any]], adapter_ids: Sequence[str] | None) -> list[dict[str, Any]]:
    if not adapter_ids:
        return [dict(row) for row in rows]
    wanted = {_clean_identifier(item, fallback="adapter").lower() for item in adapter_ids}
    selected = [dict(row) for row in rows if row.get("adapter_id") in wanted]
    missing = sorted(wanted.difference({str(row.get("adapter_id")) for row in selected}))
    if missing:
        raise SourceAdapterFixtureAuthoringError(f"adapter ids not found in fixture matrix: {', '.join(missing)}")
    return selected


def _template_for_fixture(adapter: Mapping[str, Any], fixture_type: str, sequence_number: int) -> dict[str, Any]:
    template_meta = dict(_TEMPLATE_JSON_BY_TYPE.get(fixture_type, {}))
    artifact_role = str(template_meta.get("artifact_role") or fixture_type)
    safe_adapter_id = _clean_identifier(adapter.get("adapter_id"), fallback="adapter").lower()
    safe_fixture_type = _clean_identifier(fixture_type, fallback="fixture").lower()
    template_basename = f"{safe_adapter_id}.{sequence_number:02d}.{safe_fixture_type}.template.json"
    return {
        "adapter_id": safe_adapter_id,
        "artifact_role": artifact_role,
        "fixture_status": "TEMPLATE_READY",
        "fixture_type": safe_fixture_type,
        "operator_supplied_file_required": bool(template_meta.get("operator_supplied_file_required", False)),
        "safe_template_basename": template_basename,
        "template_json": {
            "adapter_id": safe_adapter_id,
            "fixture_type": safe_fixture_type,
            "operator_notes": str(template_meta.get("notes") or "Provide explicit fixture assertions for this adapter."),
            "source_artifact_safe_basename": "",
            "source_artifact_sha256": "",
            "expected_assertions": {},
        },
    }


def _build_adapter_packet(adapter: Mapping[str, Any]) -> dict[str, Any]:
    fixture_types = list(adapter.get("fixture_types") or [])
    templates = [_template_for_fixture(adapter, fixture_type, index + 1) for index, fixture_type in enumerate(fixture_types)]
    required_file_templates = [item for item in templates if item["operator_supplied_file_required"]]
    expected_json_templates = [item for item in templates if not item["operator_supplied_file_required"]]
    return {
        "adapter_id": adapter["adapter_id"],
        "adapter_specific_module_required": adapter["adapter_specific_module_required"],
        "coverage_status": adapter["coverage_status"],
        "display_name": adapter["display_name"],
        "expected_json_template_count": len(expected_json_templates),
        "fixture_template_count": len(templates),
        "fixture_templates": templates,
        "operator_file_template_count": len(required_file_templates),
        "route_status": "READY_FOR_OPERATOR_FIXTURE_AUTHORING",
        "shared_pipeline_stages": list(adapter["shared_pipeline_stages"]),
        "source_kind": adapter["source_kind"],
    }


def _stage_route_plan(adapter_packets: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    adapters: list[dict[str, Any]] = []
    for packet in adapter_packets:
        adapters.append(
            {
                "adapter_id": packet["adapter_id"],
                "fixture_template_count": packet["fixture_template_count"],
                "route_mode": "shared_stage_fixture_execution",
                "shared_pipeline_stages": list(packet["shared_pipeline_stages"]),
            }
        )
    return {
        "schema_version": ROUTE_PLAN_SCHEMA_VERSION,
        "adapters": adapters,
        "execution_default": "local_fixture_only",
        "live_network_default": False,
        "manual_or_live_actions_started": False,
    }


def build_source_adapter_fixture_authoring(
    fixture_matrix: Mapping[str, Any],
    *,
    adapter_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Build deterministic fixture-authoring templates from an adapter fixture matrix."""

    matrix = _coerce_mapping(fixture_matrix, name="fixture_matrix_input")
    _assert_no_forbidden_keys(matrix, name="fixture_matrix_input")
    rows = _selected_rows(_load_rows(matrix), adapter_ids)
    adapter_packets = [_build_adapter_packet(row) for row in rows]
    template_rows: list[dict[str, Any]] = []
    for packet in adapter_packets:
        for template in packet["fixture_templates"]:
            template_rows.append(
                {
                    "adapter_id": template["adapter_id"],
                    "artifact_role": template["artifact_role"],
                    "fixture_type": template["fixture_type"],
                    "operator_supplied_file_required": template["operator_supplied_file_required"],
                    "safe_template_basename": template["safe_template_basename"],
                }
            )
    base = {
        "schema_version": SCHEMA_VERSION,
        "source_adapter_fixture_matrix_id": str(matrix.get("adapter_fixture_matrix_id") or ""),
        "adapter_packets": adapter_packets,
    }
    authoring_id = f"source_adapter_fixture_authoring.{_stable_hash(base)}"
    template_index = {
        "schema_version": TEMPLATE_INDEX_SCHEMA_VERSION,
        "source_adapter_fixture_authoring_id": authoring_id,
        "adapter_count": len(adapter_packets),
        "fixture_template_count": len(template_rows),
        "template_rows": template_rows,
    }
    route_plan = _stage_route_plan(adapter_packets)
    route_plan["source_adapter_fixture_authoring_id"] = authoring_id
    review_handoff = {
        "schema_version": REVIEW_HANDOFF_SCHEMA_VERSION,
        "source_adapter_fixture_authoring_id": authoring_id,
        "handoff_status": "AWAITING_OPERATOR_FIXTURE_FILES",
        "adapter_count": len(adapter_packets),
        "fixture_template_count": len(template_rows),
        "required_next_artifacts": [row["safe_template_basename"] for row in template_rows],
        "manual_or_live_actions_started": False,
        "live_network_default": False,
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "source_adapter_fixture_authoring_id": authoring_id,
        "adapter_count": len(adapter_packets),
        "fixture_template_count": len(template_rows),
        "status": "FIXTURE_AUTHORING_TEMPLATES_READY",
        "manual_or_live_actions_started": False,
        "live_network_default": False,
        "next_actions": [
            "Fill each generated template with explicit saved-source fixture basenames and expected assertions.",
            "Run authored fixtures through the shared source pipeline instead of creating per-site pipelines.",
            "Create adapter-specific code only for adapters that explicitly require a unique extraction module.",
        ],
    }
    return {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "source_adapter_fixture_authoring_id": authoring_id,
        "source_adapter_fixture_matrix_id": str(matrix.get("adapter_fixture_matrix_id") or ""),
        "adapter_count": len(adapter_packets),
        "fixture_template_count": len(template_rows),
        "adapter_packets": adapter_packets,
        "template_index": template_index,
        "shared_stage_route_plan": route_plan,
        "fixture_review_handoff": review_handoff,
        "operator_summary": operator_summary,
    }


def load_fixture_matrix_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise SourceAdapterFixtureAuthoringError("fixture matrix JSON must be an object")
    return dict(data)


def write_json_file(path: str | Path, data: Mapping[str, Any]) -> None:
    Path(path).write_bytes(_json_bytes(data))


if __name__ == "__main__":
    matrix = {
        "adapter_fixture_matrix_id": "source_adapter_fixture_matrix.example",
        "fixture_matrix": {
            "rows": [
                {
                    "adapter_id": "article",
                    "display_name": "Article",
                    "source_kind": "web",
                    "fixture_types": ["saved_article_html_or_text", "expected_content_extraction_json"],
                    "shared_pipeline_stages": ["artifact_collection", "content_extraction", "pipeline_closeout"],
                }
            ]
        },
    }
    build_source_adapter_fixture_authoring(matrix)
    print("Source Adapter Fixture Authoring self-test passed.")
