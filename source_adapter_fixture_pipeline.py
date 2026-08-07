from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "source_adapter_fixture_pipeline_v1"
PACKAGE_SCHEMA_VERSION = "source_adapter_fixture_pipeline_package_v1"
PLAN_SCHEMA_VERSION = "source_adapter_fixture_execution_plan_v1"
ASSERTION_MANIFEST_SCHEMA_VERSION = "source_adapter_fixture_assertion_manifest_v1"
HANDOFF_SCHEMA_VERSION = "source_adapter_fixture_pipeline_closeout_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_fixture_pipeline_operator_summary_v1"

_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
_SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")
_FORBIDDEN_PATH_FIELDS = {"path", "absolute_path", "local_path", "filesystem_path"}
_ALLOWED_RESULT_STATUSES = {"PASS", "FAIL", "BLOCKED", "SKIPPED"}


class SourceAdapterFixturePipelineError(ValueError):
    """Raised when adapter fixture-pipeline input is invalid."""


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
        raise SourceAdapterFixturePipelineError(f"{name} must be a JSON object")
    return dict(value)


def _coerce_sequence(value: object, *, name: str) -> list[Any]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise SourceAdapterFixturePipelineError(f"{name} must be a JSON array")
    return list(value)


def _ensure_no_local_paths(value: Mapping[str, Any], *, name: str) -> None:
    present = sorted(_FORBIDDEN_PATH_FIELDS.intersection(value.keys()))
    if present:
        raise SourceAdapterFixturePipelineError(f"{name} must not include local path fields: {', '.join(present)}")


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
        raise SourceAdapterFixturePipelineError(f"{name} is required")
    if "/" in text or "\\" in text or text in {".", ".."}:
        raise SourceAdapterFixturePipelineError(f"{name} must be a safe basename, not a path")
    return text


def _review_fixtures(fixture_review: Mapping[str, Any]) -> list[dict[str, Any]]:
    registry = _coerce_mapping(fixture_review.get("fixture_registry", {}), name="fixture_registry")
    fixtures_raw = registry.get("fixtures", fixture_review.get("fixtures", []))
    fixtures = _coerce_sequence(fixtures_raw, name="fixture_registry.fixtures")
    out: list[dict[str, Any]] = []
    for index, raw in enumerate(fixtures):
        row = _coerce_mapping(raw, name=f"fixture_registry.fixtures[{index}]")
        _assert_no_forbidden_keys(row, name=f"fixture_registry.fixtures[{index}]")
        adapter_id = _clean_identifier(row.get("adapter_id"), fallback=f"adapter_{index + 1}").lower()
        fixture_type = _clean_identifier(row.get("fixture_type"), fallback="fixture").lower()
        template_safe_basename = _safe_basename(row.get("template_safe_basename"), name="template_safe_basename")
        source_artifact_safe_basename = _safe_basename(
            row.get("source_artifact_safe_basename"),
            name="source_artifact_safe_basename",
            allow_empty=True,
        )
        source_artifact_sha256 = str(row.get("source_artifact_sha256") or "").strip().lower()
        operator_file_required = bool(row.get("operator_supplied_file_required", False))
        if operator_file_required and not _SHA256_RE.match(source_artifact_sha256):
            raise SourceAdapterFixturePipelineError("operator supplied fixture rows must include a 64-character sha256")
        expected_assertion_keys = [str(item) for item in row.get("expected_assertion_keys", [])]
        out.append(
            {
                "adapter_id": adapter_id,
                "artifact_role": str(row.get("artifact_role") or fixture_type),
                "fixture_type": fixture_type,
                "template_safe_basename": template_safe_basename,
                "operator_supplied_file_required": operator_file_required,
                "fixture_review_status": str(row.get("fixture_review_status") or "").strip().upper(),
                "source_artifact_safe_basename": source_artifact_safe_basename,
                "source_artifact_sha256": source_artifact_sha256,
                "expected_assertion_keys": sorted(expected_assertion_keys),
            }
        )
    if not out:
        raise SourceAdapterFixturePipelineError("fixture review package must include reviewed fixtures")
    return out


def _adapter_routes(fixture_review: Mapping[str, Any]) -> dict[str, list[str]]:
    reviews = _coerce_sequence(fixture_review.get("adapter_reviews", []), name="adapter_reviews")
    routes: dict[str, list[str]] = {}
    for index, raw in enumerate(reviews):
        row = _coerce_mapping(raw, name=f"adapter_reviews[{index}]")
        adapter_id = _clean_identifier(row.get("adapter_id"), fallback=f"adapter_{index + 1}").lower()
        stages_raw = _coerce_sequence(row.get("shared_pipeline_stages", []), name="shared_pipeline_stages")
        routes[adapter_id] = [_clean_identifier(stage, fallback="stage").lower() for stage in stages_raw if str(stage or "").strip()]
    return routes


def _execution_plan_rows(fixtures: Sequence[Mapping[str, Any]], routes: Mapping[str, list[str]]) -> list[dict[str, Any]]:
    by_adapter: dict[str, list[Mapping[str, Any]]] = {}
    for fixture in fixtures:
        by_adapter.setdefault(str(fixture["adapter_id"]), []).append(fixture)
    rows: list[dict[str, Any]] = []
    for adapter_id in sorted(by_adapter):
        adapter_fixtures = sorted(by_adapter[adapter_id], key=lambda item: (str(item["fixture_type"]), str(item["template_safe_basename"])))
        stages = list(routes.get(adapter_id, []))
        for stage_id in stages:
            rows.append(
                {
                    "adapter_id": adapter_id,
                    "stage_id": stage_id,
                    "fixture_count": len(adapter_fixtures),
                    "fixture_types": sorted({str(item["fixture_type"]) for item in adapter_fixtures}),
                    "template_safe_basenames": [str(item["template_safe_basename"]) for item in adapter_fixtures],
                    "execution_mode": "local_fixture_only",
                }
            )
    return rows


def _result_rows(pipeline_results: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not pipeline_results:
        return []
    results = _coerce_sequence(pipeline_results.get("stage_results", []), name="pipeline_results.stage_results")
    out: list[dict[str, Any]] = []
    for index, raw in enumerate(results):
        row = _coerce_mapping(raw, name=f"pipeline_results.stage_results[{index}]")
        _assert_no_forbidden_keys(row, name=f"pipeline_results.stage_results[{index}]")
        adapter_id = _clean_identifier(row.get("adapter_id"), fallback=f"adapter_{index + 1}").lower()
        stage_id = _clean_identifier(row.get("stage_id"), fallback="stage").lower()
        status = str(row.get("result_status") or "PASS").strip().upper()
        if status not in _ALLOWED_RESULT_STATUSES:
            raise SourceAdapterFixturePipelineError(f"result_status must be one of {', '.join(sorted(_ALLOWED_RESULT_STATUSES))}")
        issues = [str(issue).strip() for issue in row.get("issues", []) if str(issue).strip()]
        out.append(
            {
                "adapter_id": adapter_id,
                "stage_id": stage_id,
                "result_status": status,
                "assertions_checked": sorted(str(item) for item in row.get("assertions_checked", [])),
                "issue_count": len(issues) if "issue_count" not in row else int(row.get("issue_count") or 0),
                "issues": issues,
            }
        )
    return out


def _assertion_manifest(fixtures: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for fixture in fixtures:
        rows.append(
            {
                "adapter_id": str(fixture["adapter_id"]),
                "fixture_type": str(fixture["fixture_type"]),
                "template_safe_basename": str(fixture["template_safe_basename"]),
                "expected_assertion_keys": list(fixture.get("expected_assertion_keys", [])),
                "source_artifact_safe_basename": str(fixture.get("source_artifact_safe_basename") or ""),
                "source_artifact_sha256": str(fixture.get("source_artifact_sha256") or ""),
            }
        )
    return {
        "schema_version": ASSERTION_MANIFEST_SCHEMA_VERSION,
        "fixture_count": len(rows),
        "assertion_rows": rows,
    }


def build_source_adapter_fixture_pipeline(
    fixture_review: Mapping[str, Any],
    pipeline_results: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic local-only fixture pipeline package from reviewed adapter fixtures."""

    review = _coerce_mapping(fixture_review, name="fixture_review")
    results_input = _coerce_mapping(pipeline_results, name="pipeline_results") if pipeline_results is not None else None
    _assert_no_forbidden_keys(review, name="fixture_review")
    if results_input is not None:
        _assert_no_forbidden_keys(results_input, name="pipeline_results")
    fixtures = _review_fixtures(review)
    routes = _adapter_routes(review)
    execution_rows = _execution_plan_rows(fixtures, routes)
    results = _result_rows(results_input)
    review_status = str(review.get("review_status") or "").strip().upper()
    issues: list[str] = []
    if review_status != "PASSED":
        issues.append("fixture review must pass before shared fixture pipeline execution")
    adapters_without_routes = sorted({str(item["adapter_id"]) for item in fixtures if not routes.get(str(item["adapter_id"]))})
    issues.extend(f"adapter has no shared pipeline route: {adapter_id}" for adapter_id in adapters_without_routes)
    planned_keys = {(row["adapter_id"], row["stage_id"]) for row in execution_rows}
    for result in results:
        key = (result["adapter_id"], result["stage_id"])
        if key not in planned_keys:
            issues.append(f"unexpected stage result: {result['adapter_id']}:{result['stage_id']}")
        if result["result_status"] in {"FAIL", "BLOCKED"}:
            issues.append(f"stage result blocked or failed: {result['adapter_id']}:{result['stage_id']}")
        issues.extend(f"{result['adapter_id']}:{result['stage_id']}: {issue}" for issue in result.get("issues", []))
    if issues:
        status = "BLOCKED_BY_FIXTURE_REVIEW" if review_status != "PASSED" else "FAILED"
    elif results:
        status = "PASSED"
    else:
        status = "READY_FOR_LOCAL_FIXTURE_EXECUTION"
    base = {
        "schema_version": SCHEMA_VERSION,
        "source_adapter_fixture_review_id": str(review.get("source_adapter_fixture_review_id") or ""),
        "source_adapter_fixture_authoring_id": str(review.get("source_adapter_fixture_authoring_id") or ""),
        "source_adapter_fixture_matrix_id": str(review.get("source_adapter_fixture_matrix_id") or ""),
        "fixture_count": len(fixtures),
        "planned_stage_count": len(execution_rows),
        "result_count": len(results),
        "fixture_pipeline_status": status,
        "issues": issues,
    }
    pipeline_id = f"source_adapter_fixture_pipeline.{_stable_hash(base)}"
    execution_plan = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "source_adapter_fixture_pipeline_id": pipeline_id,
        "source_adapter_fixture_review_id": base["source_adapter_fixture_review_id"],
        "execution_mode": "local_fixture_only",
        "manual_or_live_actions_started": False,
        "live_network_default": False,
        "planned_stage_count": len(execution_rows),
        "stage_rows": execution_rows,
    }
    assertion_manifest = _assertion_manifest(fixtures)
    assertion_manifest["source_adapter_fixture_pipeline_id"] = pipeline_id
    closeout_handoff = {
        "schema_version": HANDOFF_SCHEMA_VERSION,
        "source_adapter_fixture_pipeline_id": pipeline_id,
        "source_adapter_fixture_review_id": base["source_adapter_fixture_review_id"],
        "handoff_status": "READY_FOR_FIXTURE_PIPELINE_CLOSEOUT" if status in {"PASSED", "READY_FOR_LOCAL_FIXTURE_EXECUTION"} else "BLOCKED_BY_FIXTURE_PIPELINE",
        "fixture_pipeline_status": status,
        "fixture_count": len(fixtures),
        "planned_stage_count": len(execution_rows),
        "result_count": len(results),
        "manual_or_live_actions_started": False,
        "live_network_default": False,
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "source_adapter_fixture_pipeline_id": pipeline_id,
        "source_adapter_fixture_review_id": base["source_adapter_fixture_review_id"],
        "fixture_pipeline_status": status,
        "fixture_count": len(fixtures),
        "planned_stage_count": len(execution_rows),
        "result_count": len(results),
        "issue_count": len(issues),
        "manual_or_live_actions_started": False,
        "live_network_default": False,
        "next_actions": [
            "Use explicit fixture results to prove adapter mappings against shared pipeline stages.",
            "Promote passed fixture pipeline packages into fixture closeout or release documentation.",
            "Keep network, browser, archive, and credential actions outside this local fixture stage.",
        ],
    }
    return {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "source_adapter_fixture_pipeline_id": pipeline_id,
        "source_adapter_fixture_review_id": base["source_adapter_fixture_review_id"],
        "source_adapter_fixture_authoring_id": base["source_adapter_fixture_authoring_id"],
        "source_adapter_fixture_matrix_id": base["source_adapter_fixture_matrix_id"],
        "fixture_pipeline_status": status,
        "fixture_count": len(fixtures),
        "planned_stage_count": len(execution_rows),
        "result_count": len(results),
        "issue_count": len(issues),
        "issues": issues,
        "fixture_execution_plan": execution_plan,
        "fixture_assertion_manifest": assertion_manifest,
        "stage_results": results,
        "fixture_pipeline_closeout_handoff": closeout_handoff,
        "operator_summary": operator_summary,
    }


def load_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise SourceAdapterFixturePipelineError("JSON input must be an object")
    return dict(data)


def write_json_file(path: str | Path, data: Mapping[str, Any]) -> None:
    Path(path).write_bytes(_json_bytes(data))


if __name__ == "__main__":
    fixture_review = {
        "source_adapter_fixture_review_id": "source_adapter_fixture_review.example",
        "source_adapter_fixture_authoring_id": "source_adapter_fixture_authoring.example",
        "source_adapter_fixture_matrix_id": "source_adapter_fixture_matrix.example",
        "review_status": "PASSED",
        "adapter_reviews": [{"adapter_id": "article", "shared_pipeline_stages": ["artifact_collection", "content_extraction"]}],
        "fixture_registry": {
            "fixtures": [
                {
                    "adapter_id": "article",
                    "fixture_type": "saved_article_html_or_text",
                    "template_safe_basename": "article.01.saved_article_html_or_text.template.json",
                    "operator_supplied_file_required": True,
                    "fixture_review_status": "PASSED",
                    "source_artifact_safe_basename": "article.fixture.html",
                    "source_artifact_sha256": "a" * 64,
                    "expected_assertion_keys": [],
                },
                {
                    "adapter_id": "article",
                    "fixture_type": "expected_content_extraction_json",
                    "template_safe_basename": "article.02.expected_content_extraction_json.template.json",
                    "operator_supplied_file_required": False,
                    "fixture_review_status": "PASSED",
                    "expected_assertion_keys": ["title"],
                },
            ]
        },
    }
    result = build_source_adapter_fixture_pipeline(fixture_review)
    assert result["fixture_pipeline_status"] == "READY_FOR_LOCAL_FIXTURE_EXECUTION", result
    print("Source Adapter Fixture Pipeline self-test passed.")
