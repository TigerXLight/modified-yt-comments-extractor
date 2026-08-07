from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "source_adapter_fixture_pipeline_closeout_v1"
PACKAGE_SCHEMA_VERSION = "source_adapter_fixture_pipeline_closeout_package_v1"
RECORD_SCHEMA_VERSION = "source_adapter_fixture_pipeline_closeout_record_v1"
TRACEABILITY_SCHEMA_VERSION = "source_adapter_fixture_pipeline_traceability_index_v1"
HANDOFF_SCHEMA_VERSION = "source_adapter_fixture_acceptance_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_fixture_pipeline_closeout_operator_summary_v1"

_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
_FORBIDDEN_PATH_FIELDS = {"path", "absolute_path", "local_path", "filesystem_path"}
_ALLOWED_PIPELINE_STATUSES = {"READY_FOR_LOCAL_FIXTURE_EXECUTION", "PASSED", "FAILED", "BLOCKED_BY_FIXTURE_REVIEW"}


class SourceAdapterFixturePipelineCloseoutError(ValueError):
    """Raised when adapter fixture pipeline closeout input is invalid."""


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
        raise SourceAdapterFixturePipelineCloseoutError(f"{name} must be a JSON object")
    return dict(value)


def _coerce_sequence(value: object, *, name: str) -> list[Any]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise SourceAdapterFixturePipelineCloseoutError(f"{name} must be a JSON array")
    return list(value)


def _ensure_no_local_paths(value: Mapping[str, Any], *, name: str) -> None:
    present = sorted(_FORBIDDEN_PATH_FIELDS.intersection(value.keys()))
    if present:
        raise SourceAdapterFixturePipelineCloseoutError(f"{name} must not include local path fields: {', '.join(present)}")


def _assert_no_forbidden_keys(value: object, *, name: str) -> None:
    if isinstance(value, Mapping):
        _ensure_no_local_paths(value, name=name)
        for key, child in value.items():
            _assert_no_forbidden_keys(child, name=f"{name}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _assert_no_forbidden_keys(child, name=f"{name}[{index}]")


def _pipeline_ids(pipeline: Mapping[str, Any]) -> dict[str, str]:
    pipeline_id = str(pipeline.get("source_adapter_fixture_pipeline_id") or "").strip()
    if not pipeline_id:
        raise SourceAdapterFixturePipelineCloseoutError("source_adapter_fixture_pipeline_id is required")
    return {
        "source_adapter_fixture_pipeline_id": pipeline_id,
        "source_adapter_fixture_review_id": str(pipeline.get("source_adapter_fixture_review_id") or ""),
        "source_adapter_fixture_authoring_id": str(pipeline.get("source_adapter_fixture_authoring_id") or ""),
        "source_adapter_fixture_matrix_id": str(pipeline.get("source_adapter_fixture_matrix_id") or ""),
    }


def _pipeline_status(pipeline: Mapping[str, Any]) -> str:
    status = str(pipeline.get("fixture_pipeline_status") or "").strip().upper()
    if status not in _ALLOWED_PIPELINE_STATUSES:
        raise SourceAdapterFixturePipelineCloseoutError(
            "fixture_pipeline_status must be one of " + ", ".join(sorted(_ALLOWED_PIPELINE_STATUSES))
        )
    return status


def _stage_rows(pipeline: Mapping[str, Any]) -> list[dict[str, Any]]:
    plan = _coerce_mapping(pipeline.get("fixture_execution_plan", {}), name="fixture_execution_plan")
    raw_rows = _coerce_sequence(plan.get("stage_rows", []), name="fixture_execution_plan.stage_rows")
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_rows):
        row = _coerce_mapping(raw, name=f"fixture_execution_plan.stage_rows[{index}]")
        rows.append(
            {
                "adapter_id": _clean_identifier(row.get("adapter_id"), fallback=f"adapter_{index + 1}").lower(),
                "stage_id": _clean_identifier(row.get("stage_id"), fallback="stage").lower(),
                "execution_mode": str(row.get("execution_mode") or ""),
                "fixture_count": int(row.get("fixture_count") or 0),
                "fixture_types": sorted(str(item) for item in row.get("fixture_types", [])),
                "template_safe_basenames": [str(item) for item in row.get("template_safe_basenames", [])],
            }
        )
    return rows


def _assertion_rows(pipeline: Mapping[str, Any]) -> list[dict[str, Any]]:
    manifest = _coerce_mapping(pipeline.get("fixture_assertion_manifest", {}), name="fixture_assertion_manifest")
    raw_rows = _coerce_sequence(manifest.get("assertion_rows", []), name="fixture_assertion_manifest.assertion_rows")
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_rows):
        row = _coerce_mapping(raw, name=f"fixture_assertion_manifest.assertion_rows[{index}]")
        rows.append(
            {
                "adapter_id": _clean_identifier(row.get("adapter_id"), fallback=f"adapter_{index + 1}").lower(),
                "fixture_type": _clean_identifier(row.get("fixture_type"), fallback="fixture").lower(),
                "template_safe_basename": str(row.get("template_safe_basename") or ""),
                "expected_assertion_keys": sorted(str(item) for item in row.get("expected_assertion_keys", [])),
                "source_artifact_safe_basename": str(row.get("source_artifact_safe_basename") or ""),
                "source_artifact_sha256": str(row.get("source_artifact_sha256") or ""),
            }
        )
    return rows


def _result_rows(pipeline: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_rows = _coerce_sequence(pipeline.get("stage_results", []), name="stage_results")
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_rows):
        row = _coerce_mapping(raw, name=f"stage_results[{index}]")
        rows.append(
            {
                "adapter_id": _clean_identifier(row.get("adapter_id"), fallback=f"adapter_{index + 1}").lower(),
                "stage_id": _clean_identifier(row.get("stage_id"), fallback="stage").lower(),
                "result_status": str(row.get("result_status") or "").strip().upper(),
                "assertions_checked": sorted(str(item) for item in row.get("assertions_checked", [])),
                "issue_count": int(row.get("issue_count") or 0),
                "issues": [str(item) for item in row.get("issues", [])],
            }
        )
    return rows


def _store_summary(pipeline_store: Mapping[str, Any] | None, *, pipeline_id: str) -> dict[str, Any]:
    if not pipeline_store:
        return {
            "store_record_supplied": False,
            "store_record_matches_pipeline": False,
            "stored_file_count": 0,
            "stored_roles": [],
        }
    store = _coerce_mapping(pipeline_store, name="pipeline_store")
    _assert_no_forbidden_keys(store, name="pipeline_store")
    stored_files = _coerce_sequence(store.get("stored_files", []), name="pipeline_store.stored_files")
    return {
        "store_record_supplied": True,
        "store_record_matches_pipeline": str(store.get("source_adapter_fixture_pipeline_id") or "") == pipeline_id,
        "stored_file_count": len(stored_files),
        "stored_roles": sorted(str(_coerce_mapping(item, name="stored_file").get("role") or "") for item in stored_files),
    }


def _closeout_status(status: str, issue_count: int, result_count: int) -> str:
    if status == "PASSED" and issue_count == 0 and result_count > 0:
        return "FIXTURE_PIPELINE_CLOSED"
    if status == "READY_FOR_LOCAL_FIXTURE_EXECUTION" and issue_count == 0:
        return "READY_FOR_LOCAL_FIXTURE_RESULTS"
    return "FIXTURE_PIPELINE_BLOCKED"


def build_source_adapter_fixture_pipeline_closeout(
    fixture_pipeline: Mapping[str, Any],
    pipeline_store: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic closeout package for a local-only adapter fixture pipeline."""

    pipeline = _coerce_mapping(fixture_pipeline, name="fixture_pipeline")
    _assert_no_forbidden_keys(pipeline, name="fixture_pipeline")
    ids = _pipeline_ids(pipeline)
    status = _pipeline_status(pipeline)
    stages = _stage_rows(pipeline)
    assertions = _assertion_rows(pipeline)
    results = _result_rows(pipeline)
    pipeline_issue_count = int(pipeline.get("issue_count") or 0)
    pipeline_issues = [str(issue) for issue in pipeline.get("issues", [])]
    store = _store_summary(pipeline_store, pipeline_id=ids["source_adapter_fixture_pipeline_id"])

    issues: list[str] = list(pipeline_issues)
    if int(pipeline.get("planned_stage_count") or 0) != len(stages):
        issues.append("planned_stage_count does not match fixture execution plan rows")
    if int(pipeline.get("fixture_count") or 0) != len(assertions):
        issues.append("fixture_count does not match assertion manifest rows")
    if int(pipeline.get("result_count") or 0) != len(results):
        issues.append("result_count does not match stage result rows")
    if pipeline_store and not store["store_record_matches_pipeline"]:
        issues.append("pipeline store record does not match source_adapter_fixture_pipeline_id")
    if pipeline_issue_count and not pipeline_issues:
        issues.append("pipeline issue_count is non-zero but issues are empty")

    computed_status = _closeout_status(status, len(issues), len(results))
    adapter_ids = sorted({row["adapter_id"] for row in stages} | {row["adapter_id"] for row in assertions})
    base = {
        **ids,
        "fixture_pipeline_status": status,
        "closeout_status": computed_status,
        "adapter_count": len(adapter_ids),
        "fixture_count": len(assertions),
        "planned_stage_count": len(stages),
        "result_count": len(results),
        "issue_count": len(issues),
    }
    closeout_id = f"source_adapter_fixture_pipeline_closeout.{_stable_hash(base)}"
    closeout_record = {
        "schema_version": RECORD_SCHEMA_VERSION,
        "source_adapter_fixture_pipeline_closeout_id": closeout_id,
        **ids,
        "fixture_pipeline_status": status,
        "closeout_status": computed_status,
        "acceptance_ready": computed_status == "FIXTURE_PIPELINE_CLOSED",
        "adapter_count": len(adapter_ids),
        "fixture_count": len(assertions),
        "planned_stage_count": len(stages),
        "result_count": len(results),
        "issue_count": len(issues),
        "issues": issues,
        "manual_or_live_actions_started": False,
        "live_network_default": False,
        "store_summary": store,
    }
    traceability_index = {
        "schema_version": TRACEABILITY_SCHEMA_VERSION,
        "source_adapter_fixture_pipeline_closeout_id": closeout_id,
        "source_adapter_fixture_pipeline_id": ids["source_adapter_fixture_pipeline_id"],
        "adapter_count": len(adapter_ids),
        "fixture_count": len(assertions),
        "planned_stage_count": len(stages),
        "result_count": len(results),
        "adapters": adapter_ids,
        "stage_rows": stages,
        "assertion_rows": assertions,
        "result_rows": results,
    }
    if computed_status == "FIXTURE_PIPELINE_CLOSED":
        handoff_status = "READY_FOR_ADAPTER_COVERAGE_ACCEPTANCE"
    elif computed_status == "READY_FOR_LOCAL_FIXTURE_RESULTS":
        handoff_status = "WAITING_FOR_LOCAL_FIXTURE_RESULTS"
    else:
        handoff_status = "BLOCKED_BY_FIXTURE_PIPELINE"
    acceptance_handoff = {
        "schema_version": HANDOFF_SCHEMA_VERSION,
        "source_adapter_fixture_pipeline_closeout_id": closeout_id,
        "source_adapter_fixture_pipeline_id": ids["source_adapter_fixture_pipeline_id"],
        "source_adapter_fixture_review_id": ids["source_adapter_fixture_review_id"],
        "handoff_status": handoff_status,
        "adapter_count": len(adapter_ids),
        "fixture_count": len(assertions),
        "accepted_adapter_count": len(adapter_ids) if computed_status == "FIXTURE_PIPELINE_CLOSED" else 0,
        "manual_or_live_actions_started": False,
        "live_network_default": False,
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "source_adapter_fixture_pipeline_closeout_id": closeout_id,
        "source_adapter_fixture_pipeline_id": ids["source_adapter_fixture_pipeline_id"],
        "closeout_status": computed_status,
        "handoff_status": handoff_status,
        "adapter_count": len(adapter_ids),
        "fixture_count": len(assertions),
        "issue_count": len(issues),
        "manual_or_live_actions_started": False,
        "live_network_default": False,
        "next_actions": [
            "Use passed fixture closeout records as adapter coverage evidence.",
            "Keep additional source adapters on shared fixture contracts unless marked adapter-specific.",
            "Do not promote blocked fixture pipelines into adapter coverage acceptance.",
        ],
    }
    return {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "source_adapter_fixture_pipeline_closeout_id": closeout_id,
        **ids,
        "fixture_pipeline_status": status,
        "closeout_status": computed_status,
        "adapter_count": len(adapter_ids),
        "fixture_count": len(assertions),
        "planned_stage_count": len(stages),
        "result_count": len(results),
        "issue_count": len(issues),
        "issues": issues,
        "closeout_record": closeout_record,
        "traceability_index": traceability_index,
        "adapter_acceptance_handoff": acceptance_handoff,
        "operator_summary": operator_summary,
    }


def load_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise SourceAdapterFixturePipelineCloseoutError("JSON input must be an object")
    return dict(data)


def write_json_file(path: str | Path, data: Mapping[str, Any]) -> None:
    Path(path).write_bytes(_json_bytes(data))


if __name__ == "__main__":
    pipeline = {
        "source_adapter_fixture_pipeline_id": "source_adapter_fixture_pipeline.example",
        "source_adapter_fixture_review_id": "source_adapter_fixture_review.example",
        "fixture_pipeline_status": "PASSED",
        "fixture_count": 1,
        "planned_stage_count": 1,
        "result_count": 1,
        "issue_count": 0,
        "issues": [],
        "fixture_execution_plan": {"stage_rows": [{"adapter_id": "article", "stage_id": "content_extraction", "execution_mode": "local_fixture_only", "fixture_count": 1, "fixture_types": ["expected_content_extraction_json"], "template_safe_basenames": ["article.expected.json"]}]},
        "fixture_assertion_manifest": {"assertion_rows": [{"adapter_id": "article", "fixture_type": "expected_content_extraction_json", "template_safe_basename": "article.expected.json", "expected_assertion_keys": ["title"]}]},
        "stage_results": [{"adapter_id": "article", "stage_id": "content_extraction", "result_status": "PASS", "assertions_checked": ["title"], "issue_count": 0, "issues": []}],
    }
    result = build_source_adapter_fixture_pipeline_closeout(pipeline)
    assert result["closeout_status"] == "FIXTURE_PIPELINE_CLOSED", result
    print("Source Adapter Fixture Pipeline Closeout self-test passed.")
