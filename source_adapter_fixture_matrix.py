from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = "source_adapter_fixture_matrix_v1"
REGISTRY_SCHEMA_VERSION = "source_adapter_registry_v1"
FIXTURE_MATRIX_SCHEMA_VERSION = "source_adapter_fixture_requirements_matrix_v1"
AUTHORING_PLAN_SCHEMA_VERSION = "source_adapter_fixture_authoring_plan_v1"
PIPELINE_BINDING_SCHEMA_VERSION = "source_adapter_shared_pipeline_binding_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_fixture_matrix_operator_summary_v1"

_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
_FORBIDDEN_PATH_FIELDS = {"path", "absolute_path", "local_path", "filesystem_path"}
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
_ALLOWED_SOURCE_KINDS = {"web", "social_thread", "video", "document", "local_artifact"}

SHARED_PIPELINE_STAGES: tuple[dict[str, str], ...] = (
    {"stage_id": "source_discovery", "label": "Source discovery", "shared_module": "source_adapter_coverage"},
    {"stage_id": "lightweight_browser_capture", "label": "Lightweight in-app browser capture", "shared_module": "lightweight_in_app_browser_capture"},
    {"stage_id": "artifact_collection", "label": "Explicit artifact collection", "shared_module": "source_artifact_collection"},
    {"stage_id": "content_extraction", "label": "Article/content extraction", "shared_module": "source_content_extraction"},
    {"stage_id": "comments_extraction", "label": "Comments/replies extraction", "shared_module": "source_comment_extraction"},
    {"stage_id": "capture_bundle", "label": "Capture bundle", "shared_module": "source_capture_bundle"},
    {"stage_id": "total_export_package", "label": "Total Export package", "shared_module": "source_total_export_package"},
    {"stage_id": "evidence_queue", "label": "Evidence Queue integration", "shared_module": "source_evidence_queue"},
    {"stage_id": "evidence_review", "label": "Evidence Review package/decision", "shared_module": "source_evidence_review"},
    {"stage_id": "approved_release", "label": "Approved release package", "shared_module": "source_approved_release"},
    {"stage_id": "release_index", "label": "Release index/export bundle", "shared_module": "source_release_index"},
    {"stage_id": "release_audit", "label": "Release audit/traceability", "shared_module": "source_release_audit"},
    {"stage_id": "archive_handoff", "label": "Manual archive handoff", "shared_module": "source_archive_handoff"},
    {"stage_id": "archive_result_intake", "label": "Manual archive result intake", "shared_module": "source_archive_result_intake"},
    {"stage_id": "archive_review", "label": "Archive review package/decision", "shared_module": "source_archive_review"},
    {"stage_id": "pipeline_closeout", "label": "Pipeline closeout", "shared_module": "source_pipeline_closeout"},
)

_BASE_ARTIFACT_ROLES = (
    "article_html_or_text",
    "metadata_json",
    "screenshot",
)

_KIND_DEFAULTS: dict[str, dict[str, tuple[str, ...]]] = {
    "web": {
        "artifact_roles": ("article_html_or_text", "metadata_json", "screenshot"),
        "fixture_types": (
            "saved_article_html_or_text",
            "expected_content_extraction_json",
            "expected_total_export_package_json",
            "expected_pipeline_closeout_json",
        ),
    },
    "social_thread": {
        "artifact_roles": ("article_html_or_text", "comments_json_or_text", "metadata_json", "screenshot"),
        "fixture_types": (
            "saved_article_html_or_text",
            "saved_comments_json_or_text",
            "expected_content_extraction_json",
            "expected_comment_extraction_json",
            "expected_total_export_package_json",
            "expected_review_release_archive_json",
            "expected_pipeline_closeout_json",
        ),
    },
    "video": {
        "artifact_roles": ("article_html_or_text", "comments_json_or_text", "metadata_json", "screenshot"),
        "fixture_types": (
            "saved_video_page_html_or_text",
            "saved_comments_json_or_text",
            "expected_content_extraction_json",
            "expected_comment_extraction_json",
            "expected_total_export_package_json",
            "expected_pipeline_closeout_json",
        ),
    },
    "document": {
        "artifact_roles": ("article_html_or_text", "metadata_json", "screenshot"),
        "fixture_types": (
            "saved_document_text_or_html",
            "expected_content_extraction_json",
            "expected_total_export_package_json",
            "expected_pipeline_closeout_json",
        ),
    },
    "local_artifact": {
        "artifact_roles": ("article_html_or_text", "metadata_json"),
        "fixture_types": (
            "saved_local_artifact_text_or_html",
            "expected_content_extraction_json",
            "expected_total_export_package_json",
            "expected_pipeline_closeout_json",
        ),
    },
}


class SourceAdapterFixtureMatrixError(ValueError):
    """Raised when adapter fixture-matrix input is invalid."""


def _json_bytes(data: Mapping[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"


def _stable_hash(data: Mapping[str, Any], *, length: int = 12) -> str:
    return hashlib.sha256(_json_bytes(data)).hexdigest()[:length]


def _clean_identifier(value: object, *, fallback: str) -> str:
    text = str(value or "").strip() or fallback
    text = _SAFE_ID_RE.sub(".", text).strip("._-")
    return text or fallback


def _coerce_mapping(value: Mapping[str, Any] | None, *, name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a JSON object")
    return dict(value)


def _coerce_sequence(value: object, *, name: str) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise SourceAdapterFixtureMatrixError(f"{name} must be a JSON array")
    return list(value)


def _ensure_no_local_paths(value: Mapping[str, Any], *, name: str) -> None:
    present = sorted(_FORBIDDEN_PATH_FIELDS.intersection(value.keys()))
    if present:
        raise SourceAdapterFixtureMatrixError(f"{name} must not include local path fields: {', '.join(present)}")


def _as_bool(value: object, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _normalise_text_list(value: object, *, name: str, lower: bool = False) -> list[str]:
    items = _coerce_sequence(value, name=name)
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item or "").strip()
        if lower:
            text = text.lower()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _normalise_domains(value: object) -> list[str]:
    domains: list[str] = []
    for raw in _normalise_text_list(value, name="domains", lower=True):
        domain = raw.replace("https://", "").replace("http://", "").split("/", 1)[0].strip().strip(".")
        if not domain:
            continue
        domains.append(domain)
    return sorted(dict.fromkeys(domains))


def _normalise_url_patterns(value: object) -> list[str]:
    patterns = _normalise_text_list(value, name="url_patterns")
    for pattern in patterns:
        if " " in pattern:
            raise SourceAdapterFixtureMatrixError("url_patterns must not contain spaces")
    return patterns


def _normalise_source_kind(value: object) -> str:
    kind = str(value or "web").strip().lower()
    if kind not in _ALLOWED_SOURCE_KINDS:
        raise SourceAdapterFixtureMatrixError(f"unsupported source_kind: {kind}")
    return kind


def _normalise_artifact_roles(value: object, *, source_kind: str) -> list[str]:
    roles = _normalise_text_list(value, name="artifact_roles")
    if not roles:
        roles = list(_KIND_DEFAULTS[source_kind]["artifact_roles"])
    clean: list[str] = []
    seen: set[str] = set()
    for role in roles:
        role_id = _clean_identifier(role, fallback="artifact").lower()
        if role_id not in seen:
            seen.add(role_id)
            clean.append(role_id)
    return clean


def _normalise_fixture_overrides(value: object) -> list[str]:
    overrides = _normalise_text_list(value, name="fixture_overrides")
    clean: list[str] = []
    seen: set[str] = set()
    for fixture in overrides:
        fixture_id = _clean_identifier(fixture, fallback="fixture").lower()
        if fixture_id not in seen:
            seen.add(fixture_id)
            clean.append(fixture_id)
    return clean


def _fixture_types_for_adapter(adapter: Mapping[str, Any]) -> list[str]:
    source_kind = str(adapter["source_kind"])
    fixtures = list(_KIND_DEFAULTS[source_kind]["fixture_types"])
    roles = set(adapter.get("artifact_roles") or [])
    if "comments_json_or_text" in roles and "saved_comments_json_or_text" not in fixtures:
        fixtures.append("saved_comments_json_or_text")
    for override in adapter.get("fixture_overrides", []):
        if override not in fixtures:
            fixtures.append(override)
    return fixtures


def _coverage_status(adapter: Mapping[str, Any], fixture_types: Sequence[str]) -> str:
    if adapter.get("adapter_specific_module_required"):
        return "NEEDS_ADAPTER_MODULE"
    if len(fixture_types) >= 4:
        return "READY_FOR_FIXTURE_AUTHORING"
    return "NEEDS_FIXTURE_MAPPING"


def normalise_adapter_spec(raw: Mapping[str, Any], *, index: int) -> dict[str, Any]:
    spec = _coerce_mapping(raw, name=f"adapter_specs[{index}]")
    _ensure_no_local_paths(spec, name=f"adapter_specs[{index}]")
    adapter_id = _clean_identifier(spec.get("adapter_id") or spec.get("id"), fallback=f"adapter_{index + 1}").lower()
    display_name = str(spec.get("display_name") or adapter_id.replace("_", " ").title()).strip()
    source_kind = _normalise_source_kind(spec.get("source_kind"))
    domains = _normalise_domains(spec.get("domains"))
    url_patterns = _normalise_url_patterns(spec.get("url_patterns"))
    capture_surfaces = _normalise_text_list(spec.get("capture_surfaces"), name="capture_surfaces")
    extraction_notes = _normalise_text_list(spec.get("extraction_notes"), name="extraction_notes")
    fixture_overrides = _normalise_fixture_overrides(spec.get("fixture_overrides"))
    artifact_roles = _normalise_artifact_roles(spec.get("artifact_roles"), source_kind=source_kind)
    unique_extraction_surface = _as_bool(spec.get("unique_extraction_surface"), default=False)
    requires_lightweight_browser = _as_bool(spec.get("requires_lightweight_browser"), default=source_kind in {"web", "social_thread", "video"})
    operator_only = _as_bool(spec.get("operator_only"), default=True)
    if not domains and source_kind != "local_artifact":
        raise SourceAdapterFixtureMatrixError(f"adapter {adapter_id} must include at least one domain")
    return {
        "adapter_id": adapter_id,
        "display_name": display_name,
        "source_kind": source_kind,
        "domains": domains,
        "url_patterns": url_patterns,
        "capture_surfaces": capture_surfaces,
        "artifact_roles": artifact_roles,
        "fixture_overrides": fixture_overrides,
        "extraction_notes": extraction_notes,
        "requires_lightweight_browser": requires_lightweight_browser,
        "operator_only": operator_only,
        "adapter_specific_module_required": unique_extraction_surface,
        "adapter_specific_module_reason": "unique_extraction_surface" if unique_extraction_surface else "shared_stage_mapping_only",
        "live_network_default": False,
    }


def _normalise_adapter_specs(adapter_specs: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    adapters = [normalise_adapter_spec(raw, index=index) for index, raw in enumerate(adapter_specs)]
    if not adapters:
        raise SourceAdapterFixtureMatrixError("at least one adapter spec is required")
    ids = [adapter["adapter_id"] for adapter in adapters]
    duplicates = sorted({adapter_id for adapter_id in ids if ids.count(adapter_id) > 1})
    if duplicates:
        raise SourceAdapterFixtureMatrixError(f"duplicate adapter_id values: {', '.join(duplicates)}")
    return sorted(adapters, key=lambda item: item["adapter_id"])


def load_adapter_specs_json(path: str | Path) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, Mapping):
        raw_specs = data.get("adapter_specs") or data.get("adapters")
    else:
        raw_specs = data
    if isinstance(raw_specs, str) or not isinstance(raw_specs, Sequence):
        raise SourceAdapterFixtureMatrixError("adapter specs JSON must be an array or an object containing adapter_specs/adapters")
    return _normalise_adapter_specs(raw_specs)  # type: ignore[arg-type]


def build_source_adapter_fixture_matrix(
    adapter_specs: Iterable[Mapping[str, Any]],
    *,
    pipeline_closeout: Mapping[str, Any] | None = None,
    notes: Iterable[str] | None = None,
) -> dict[str, Any]:
    pipeline = _coerce_mapping(pipeline_closeout, name="pipeline_closeout")
    if pipeline:
        _ensure_no_local_paths(pipeline, name="pipeline_closeout")
    adapters = _normalise_adapter_specs(adapter_specs)
    adapter_rows: list[dict[str, Any]] = []
    for adapter in adapters:
        fixture_types = _fixture_types_for_adapter(adapter)
        missing_shared_stages = [stage["stage_id"] for stage in SHARED_PIPELINE_STAGES]
        adapter_rows.append(
            {
                "adapter_id": adapter["adapter_id"],
                "display_name": adapter["display_name"],
                "source_kind": adapter["source_kind"],
                "fixture_types": fixture_types,
                "fixture_count": len(fixture_types),
                "artifact_roles": adapter["artifact_roles"],
                "required_fixture_files_started": False,
                "fixture_authoring_required": True,
                "shared_pipeline_stages": [stage["stage_id"] for stage in SHARED_PIPELINE_STAGES],
                "adapter_specific_module_required": adapter["adapter_specific_module_required"],
                "adapter_specific_module_reason": adapter["adapter_specific_module_reason"],
                "coverage_status": _coverage_status(adapter, fixture_types),
                "missing_fixture_count": len(fixture_types),
                "missing_shared_stage_count": len(missing_shared_stages),
            }
        )
    matrix_core = {
        "adapters": adapters,
        "adapter_fixture_rows": adapter_rows,
        "pipeline_closeout_id": pipeline.get("pipeline_closeout_id") or pipeline.get("source_pipeline_closeout_id") or "",
        "notes": [str(note).strip() for note in (notes or []) if str(note).strip()],
    }
    matrix_id = f"source_adapter_fixture_matrix.{_stable_hash(matrix_core)}"
    return {
        "schema_version": SCHEMA_VERSION,
        "adapter_fixture_matrix_id": matrix_id,
        "coverage_strategy": "one_framework_many_adapter_specs",
        "adapter_count": len(adapters),
        "pipeline_closeout_id": matrix_core["pipeline_closeout_id"],
        "adapters": adapters,
        "adapter_registry": {
            "schema_version": REGISTRY_SCHEMA_VERSION,
            "adapter_count": len(adapters),
            "adapters": adapters,
        },
        "fixture_matrix": {
            "schema_version": FIXTURE_MATRIX_SCHEMA_VERSION,
            "adapter_count": len(adapters),
            "rows": adapter_rows,
        },
        "fixture_authoring_plan": {
            "schema_version": AUTHORING_PLAN_SCHEMA_VERSION,
            "status": "FIXTURE_AUTHORING_REQUIRED",
            "manual_or_live_actions_started": False,
            "live_network_default": False,
            "per_adapter_work": "metadata mapping plus fixture coverage",
            "next_actions": [
                "Author explicit saved-source fixtures for each adapter row.",
                "Route fixture outputs through the shared artifact/content/comment/capture/review/release/archive pipeline.",
                "Create adapter-specific extraction modules only for rows marked NEEDS_ADAPTER_MODULE.",
            ],
            "adapters": [
                {
                    "adapter_id": row["adapter_id"],
                    "fixture_types": row["fixture_types"],
                    "coverage_status": row["coverage_status"],
                }
                for row in adapter_rows
            ],
        },
        "shared_pipeline_binding": {
            "schema_version": PIPELINE_BINDING_SCHEMA_VERSION,
            "stage_count": len(SHARED_PIPELINE_STAGES),
            "stages": list(SHARED_PIPELINE_STAGES),
            "binding_mode": "adapter_specs_to_shared_stage_contracts",
            "per_adapter_code_default": "not_required",
        },
        "operator_summary": {
            "schema_version": SUMMARY_SCHEMA_VERSION,
            "status": "ADAPTER_FIXTURE_MATRIX_READY",
            "manual_or_live_actions_started": False,
            "live_network_default": False,
            "adapter_count": len(adapters),
            "adapter_specific_module_count": sum(1 for adapter in adapters if adapter["adapter_specific_module_required"]),
            "next_actions": [
                "Use this matrix to decide which fixtures are needed per source adapter.",
                "Keep future site work as adapter specs plus shared-stage fixtures unless a unique extraction surface requires code.",
                "Do not repeat the MSN-specific pipeline for each new source.",
            ],
        },
    }


def write_json_file(path: str | Path, data: Mapping[str, Any]) -> dict[str, Any]:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = _json_bytes(data)
    destination.write_bytes(payload)
    return {
        "filename": destination.name,
        "role": destination.stem,
        "byte_count": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


__all__ = [
    "SCHEMA_VERSION",
    "SHARED_PIPELINE_STAGES",
    "SourceAdapterFixtureMatrixError",
    "build_source_adapter_fixture_matrix",
    "load_adapter_specs_json",
    "normalise_adapter_spec",
    "write_json_file",
]
