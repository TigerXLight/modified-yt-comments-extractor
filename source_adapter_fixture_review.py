from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "source_adapter_fixture_review_v1"
PACKAGE_SCHEMA_VERSION = "source_adapter_fixture_review_package_v1"
REGISTRY_SCHEMA_VERSION = "source_adapter_authored_fixture_registry_v1"
REPORT_SCHEMA_VERSION = "source_adapter_fixture_review_report_v1"
PIPELINE_HANDOFF_SCHEMA_VERSION = "source_adapter_fixture_pipeline_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_fixture_review_operator_summary_v1"

_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
_SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")
_FORBIDDEN_PATH_FIELDS = {"path", "absolute_path", "local_path", "filesystem_path"}


class SourceAdapterFixtureReviewError(ValueError):
    """Raised when adapter fixture-review input is invalid."""


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
        raise SourceAdapterFixtureReviewError(f"{name} must be a JSON object")
    return dict(value)


def _coerce_sequence(value: object, *, name: str) -> list[Any]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise SourceAdapterFixtureReviewError(f"{name} must be a JSON array")
    return list(value)


def _ensure_no_local_paths(value: Mapping[str, Any], *, name: str) -> None:
    present = sorted(_FORBIDDEN_PATH_FIELDS.intersection(value.keys()))
    if present:
        raise SourceAdapterFixtureReviewError(f"{name} must not include local path fields: {', '.join(present)}")


def _assert_no_forbidden_keys(value: object, *, name: str) -> None:
    if isinstance(value, Mapping):
        _ensure_no_local_paths(value, name=name)
        for key, child in value.items():
            _assert_no_forbidden_keys(child, name=f"{name}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _assert_no_forbidden_keys(child, name=f"{name}[{index}]")


def _safe_basename(value: object, *, name: str, allow_empty: bool = False) -> str:
    text = str(value or "").strip()
    if not text:
        if allow_empty:
            return ""
        raise SourceAdapterFixtureReviewError(f"{name} is required")
    if "/" in text or "\\" in text or text in {".", ".."}:
        raise SourceAdapterFixtureReviewError(f"{name} must be a safe basename, not a path")
    return text


def _template_rows(authoring: Mapping[str, Any]) -> list[dict[str, Any]]:
    index = _coerce_mapping(authoring.get("template_index", {}), name="template_index")
    rows = _coerce_sequence(index.get("template_rows", []), name="template_index.template_rows")
    templates: list[dict[str, Any]] = []
    for raw_index, raw in enumerate(rows):
        row = _coerce_mapping(raw, name=f"template_index.template_rows[{raw_index}]")
        _ensure_no_local_paths(row, name=f"template_index.template_rows[{raw_index}]")
        adapter_id = _clean_identifier(row.get("adapter_id"), fallback=f"adapter_{raw_index + 1}").lower()
        fixture_type = _clean_identifier(row.get("fixture_type"), fallback="fixture").lower()
        safe_template_basename = _safe_basename(row.get("safe_template_basename"), name="safe_template_basename")
        templates.append(
            {
                "adapter_id": adapter_id,
                "artifact_role": str(row.get("artifact_role") or fixture_type),
                "fixture_type": fixture_type,
                "operator_supplied_file_required": bool(row.get("operator_supplied_file_required", False)),
                "safe_template_basename": safe_template_basename,
            }
        )
    if not templates:
        raise SourceAdapterFixtureReviewError("fixture authoring package must include template rows")
    return templates


def _stage_routes(authoring: Mapping[str, Any]) -> dict[str, list[str]]:
    route_plan = _coerce_mapping(authoring.get("shared_stage_route_plan", {}), name="shared_stage_route_plan")
    adapters = _coerce_sequence(route_plan.get("adapters", []), name="shared_stage_route_plan.adapters")
    routes: dict[str, list[str]] = {}
    for index, raw in enumerate(adapters):
        adapter = _coerce_mapping(raw, name=f"shared_stage_route_plan.adapters[{index}]")
        adapter_id = _clean_identifier(adapter.get("adapter_id"), fallback=f"adapter_{index + 1}").lower()
        stages_raw = _coerce_sequence(adapter.get("shared_pipeline_stages", []), name="shared_pipeline_stages")
        stages = [_clean_identifier(item, fallback="stage").lower() for item in stages_raw if str(item or "").strip()]
        routes[adapter_id] = stages
    return routes


def _authored_fixture_rows(authored_fixtures: Mapping[str, Any]) -> list[dict[str, Any]]:
    fixtures = _coerce_sequence(authored_fixtures.get("fixtures", []), name="authored_fixtures.fixtures")
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(fixtures):
        row = _coerce_mapping(raw, name=f"authored_fixtures.fixtures[{index}]")
        _assert_no_forbidden_keys(row, name=f"authored_fixtures.fixtures[{index}]")
        adapter_id = _clean_identifier(row.get("adapter_id"), fallback=f"adapter_{index + 1}").lower()
        fixture_type = _clean_identifier(row.get("fixture_type"), fallback="fixture").lower()
        template_basename = _safe_basename(row.get("template_safe_basename") or row.get("safe_template_basename"), name="template_safe_basename")
        source_artifact_safe_basename = _safe_basename(
            row.get("source_artifact_safe_basename"),
            name="source_artifact_safe_basename",
            allow_empty=True,
        )
        source_artifact_sha256 = str(row.get("source_artifact_sha256") or "").strip().lower()
        expected_assertions = row.get("expected_assertions", {})
        if not isinstance(expected_assertions, Mapping):
            raise SourceAdapterFixtureReviewError("expected_assertions must be a JSON object")
        rows.append(
            {
                "adapter_id": adapter_id,
                "fixture_type": fixture_type,
                "template_safe_basename": template_basename,
                "fixture_status": str(row.get("fixture_status") or "AUTHORED").strip().upper(),
                "source_artifact_safe_basename": source_artifact_safe_basename,
                "source_artifact_sha256": source_artifact_sha256,
                "expected_assertions": dict(expected_assertions),
                "operator_notes": str(row.get("operator_notes") or "").strip(),
            }
        )
    return rows


def _review_fixture(template: Mapping[str, Any], authored_by_template: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    template_basename = str(template["safe_template_basename"])
    authored = authored_by_template.get(template_basename)
    issues: list[str] = []
    if authored is None:
        issues.append("missing authored fixture")
        authored = {}
    if authored.get("fixture_status") not in {"AUTHORED", "READY_FOR_REVIEW", "REVIEWED"}:
        issues.append("fixture_status must be AUTHORED, READY_FOR_REVIEW, or REVIEWED")
    operator_file_required = bool(template.get("operator_supplied_file_required", False))
    source_artifact_safe_basename = str(authored.get("source_artifact_safe_basename") or "")
    source_artifact_sha256 = str(authored.get("source_artifact_sha256") or "")
    if operator_file_required:
        if not source_artifact_safe_basename:
            issues.append("source artifact safe basename is required")
        if not _SHA256_RE.match(source_artifact_sha256):
            issues.append("source artifact sha256 must be 64 hex characters")
    expected_assertions = authored.get("expected_assertions", {})
    if not isinstance(expected_assertions, Mapping):
        issues.append("expected_assertions must be a JSON object")
        expected_assertions = {}
    if not operator_file_required and not expected_assertions:
        issues.append("expected assertion fixture must include expected_assertions")
    return {
        "adapter_id": str(template["adapter_id"]),
        "artifact_role": str(template["artifact_role"]),
        "fixture_type": str(template["fixture_type"]),
        "template_safe_basename": template_basename,
        "operator_supplied_file_required": operator_file_required,
        "fixture_review_status": "PASSED" if not issues else "BLOCKED",
        "issue_count": len(issues),
        "issues": issues,
        "source_artifact_safe_basename": source_artifact_safe_basename,
        "source_artifact_sha256": source_artifact_sha256,
        "expected_assertion_keys": sorted(str(key) for key in dict(expected_assertions).keys()),
    }


def _group_by_adapter(rows: Sequence[Mapping[str, Any]], routes: Mapping[str, list[str]]) -> list[dict[str, Any]]:
    adapters: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        adapters.setdefault(str(row["adapter_id"]), []).append(row)
    out: list[dict[str, Any]] = []
    for adapter_id in sorted(adapters):
        adapter_rows = list(adapters[adapter_id])
        issue_count = sum(int(row.get("issue_count", 0)) for row in adapter_rows)
        out.append(
            {
                "adapter_id": adapter_id,
                "fixture_count": len(adapter_rows),
                "blocked_fixture_count": sum(1 for row in adapter_rows if row.get("fixture_review_status") != "PASSED"),
                "issue_count": issue_count,
                "review_status": "PASSED" if issue_count == 0 else "BLOCKED",
                "shared_pipeline_stages": list(routes.get(adapter_id, [])),
            }
        )
    return out


def build_source_adapter_fixture_review(
    fixture_authoring: Mapping[str, Any],
    authored_fixtures: Mapping[str, Any],
) -> dict[str, Any]:
    """Review explicitly authored adapter fixtures before shared-pipeline fixture execution."""

    authoring = _coerce_mapping(fixture_authoring, name="fixture_authoring")
    authored = _coerce_mapping(authored_fixtures, name="authored_fixtures")
    _assert_no_forbidden_keys(authoring, name="fixture_authoring")
    _assert_no_forbidden_keys(authored, name="authored_fixtures")
    templates = _template_rows(authoring)
    routes = _stage_routes(authoring)
    authored_rows = _authored_fixture_rows(authored)
    authored_by_template = {str(row["template_safe_basename"]): row for row in authored_rows}
    reviewed_rows = [_review_fixture(template, authored_by_template) for template in templates]
    extra_templates = sorted(set(authored_by_template).difference(str(template["safe_template_basename"]) for template in templates))
    global_issues = [f"unexpected authored fixture template: {name}" for name in extra_templates]
    fixture_issues = [f"{row['template_safe_basename']}: {issue}" for row in reviewed_rows for issue in row.get("issues", [])]
    issues = global_issues + fixture_issues
    adapter_reviews = _group_by_adapter(reviewed_rows, routes)
    base = {
        "schema_version": SCHEMA_VERSION,
        "source_adapter_fixture_authoring_id": str(authoring.get("source_adapter_fixture_authoring_id") or ""),
        "source_adapter_fixture_matrix_id": str(authoring.get("source_adapter_fixture_matrix_id") or ""),
        "adapter_reviews": adapter_reviews,
        "fixtures": reviewed_rows,
        "issues": issues,
    }
    review_id = f"source_adapter_fixture_review.{_stable_hash(base)}"
    registry = {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "source_adapter_fixture_review_id": review_id,
        "source_adapter_fixture_authoring_id": base["source_adapter_fixture_authoring_id"],
        "fixture_count": len(reviewed_rows),
        "fixtures": reviewed_rows,
    }
    pipeline_handoff = {
        "schema_version": PIPELINE_HANDOFF_SCHEMA_VERSION,
        "source_adapter_fixture_review_id": review_id,
        "source_adapter_fixture_authoring_id": base["source_adapter_fixture_authoring_id"],
        "handoff_status": "READY_FOR_SHARED_PIPELINE_FIXTURE_RUN" if not issues else "BLOCKED_BY_FIXTURE_REVIEW",
        "adapter_count": len(adapter_reviews),
        "fixture_count": len(reviewed_rows),
        "shared_pipeline_execution_default": "local_fixture_only",
        "manual_or_live_actions_started": False,
        "live_network_default": False,
    }
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "source_adapter_fixture_review_id": review_id,
        "source_adapter_fixture_authoring_id": base["source_adapter_fixture_authoring_id"],
        "review_status": "PASSED" if not issues else "BLOCKED",
        "adapter_reviews": adapter_reviews,
        "issue_count": len(issues),
        "issues": issues,
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "source_adapter_fixture_review_id": review_id,
        "source_adapter_fixture_authoring_id": base["source_adapter_fixture_authoring_id"],
        "adapter_count": len(adapter_reviews),
        "fixture_count": len(reviewed_rows),
        "status": "FIXTURES_READY_FOR_SHARED_PIPELINE" if not issues else "FIXTURES_BLOCKED_FOR_REVIEW",
        "manual_or_live_actions_started": False,
        "live_network_default": False,
        "next_actions": [
            "Run reviewed fixtures through the shared local source pipeline contracts.",
            "Keep adapter work to fixtures and metadata unless review marks a unique extraction module as required.",
            "Do not launch browsers or external archive services from fixture review.",
        ],
    }
    return {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "source_adapter_fixture_review_id": review_id,
        "source_adapter_fixture_authoring_id": base["source_adapter_fixture_authoring_id"],
        "source_adapter_fixture_matrix_id": base["source_adapter_fixture_matrix_id"],
        "adapter_count": len(adapter_reviews),
        "fixture_count": len(reviewed_rows),
        "review_status": report["review_status"],
        "issue_count": len(issues),
        "issues": issues,
        "adapter_reviews": adapter_reviews,
        "fixture_registry": registry,
        "fixture_pipeline_handoff": pipeline_handoff,
        "fixture_review_report": report,
        "operator_summary": operator_summary,
    }


def load_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise SourceAdapterFixtureReviewError("JSON input must be an object")
    return dict(data)


def write_json_file(path: str | Path, data: Mapping[str, Any]) -> None:
    Path(path).write_bytes(_json_bytes(data))


if __name__ == "__main__":
    authoring = {
        "source_adapter_fixture_authoring_id": "source_adapter_fixture_authoring.example",
        "source_adapter_fixture_matrix_id": "source_adapter_fixture_matrix.example",
        "template_index": {
            "template_rows": [
                {
                    "adapter_id": "article",
                    "artifact_role": "article_html_or_text",
                    "fixture_type": "saved_article_html_or_text",
                    "operator_supplied_file_required": True,
                    "safe_template_basename": "article.01.saved_article_html_or_text.template.json",
                },
                {
                    "adapter_id": "article",
                    "artifact_role": "expected_content_extraction_json",
                    "fixture_type": "expected_content_extraction_json",
                    "operator_supplied_file_required": False,
                    "safe_template_basename": "article.02.expected_content_extraction_json.template.json",
                },
            ]
        },
        "shared_stage_route_plan": {
            "adapters": [{"adapter_id": "article", "shared_pipeline_stages": ["artifact_collection", "content_extraction"]}]
        },
    }
    authored = {
        "fixtures": [
            {
                "adapter_id": "article",
                "fixture_type": "saved_article_html_or_text",
                "template_safe_basename": "article.01.saved_article_html_or_text.template.json",
                "source_artifact_safe_basename": "article.fixture.html",
                "source_artifact_sha256": "a" * 64,
                "expected_assertions": {},
            },
            {
                "adapter_id": "article",
                "fixture_type": "expected_content_extraction_json",
                "template_safe_basename": "article.02.expected_content_extraction_json.template.json",
                "expected_assertions": {"title": "Fixture title"},
            },
        ]
    }
    result = build_source_adapter_fixture_review(authoring, authored)
    assert result["review_status"] == "PASSED", result
    print("Source Adapter Fixture Review self-test passed.")
