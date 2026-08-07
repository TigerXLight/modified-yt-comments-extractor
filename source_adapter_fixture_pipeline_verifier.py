from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

_SCHEMA_VERSION = "source_adapter_fixture_pipeline_verifier_v1"
_REQUIRED_TOP_LEVEL = {
    "schema_version",
    "source_adapter_fixture_pipeline_id",
    "source_adapter_fixture_review_id",
    "fixture_pipeline_status",
    "fixture_count",
    "planned_stage_count",
    "issue_count",
    "issues",
    "fixture_execution_plan",
    "fixture_assertion_manifest",
    "fixture_pipeline_closeout_handoff",
    "operator_summary",
}
_ALLOWED_STATUSES = {"READY_FOR_LOCAL_FIXTURE_EXECUTION", "PASSED", "FAILED", "BLOCKED_BY_FIXTURE_REVIEW"}
_FORBIDDEN_PATH_FIELDS = {"path", "absolute_path", "local_path", "filesystem_path"}
_SAFE_BASENAME_RE = re.compile(r"^[^/\\]+$")


def _coerce_mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _collect_forbidden_path_fields(value: object, *, prefix: str = "$", issues: list[str]) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in _FORBIDDEN_PATH_FIELDS:
                issues.append(f"forbidden local path field: {prefix}.{key}")
            _collect_forbidden_path_fields(child, prefix=f"{prefix}.{key}", issues=issues)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _collect_forbidden_path_fields(child, prefix=f"{prefix}[{index}]", issues=issues)


def verify_source_adapter_fixture_pipeline(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    data = _coerce_mapping(package)
    missing = sorted(_REQUIRED_TOP_LEVEL.difference(data.keys()))
    issues.extend(f"missing required field: {field}" for field in missing)
    _collect_forbidden_path_fields(data, issues=issues)
    if data.get("schema_version") != "source_adapter_fixture_pipeline_package_v1":
        issues.append("schema_version must be source_adapter_fixture_pipeline_package_v1")
    pipeline_id = str(data.get("source_adapter_fixture_pipeline_id") or "")
    if not pipeline_id.startswith("source_adapter_fixture_pipeline."):
        issues.append("source_adapter_fixture_pipeline_id must use source_adapter_fixture_pipeline prefix")
    status = str(data.get("fixture_pipeline_status") or "")
    if status not in _ALLOWED_STATUSES:
        issues.append("fixture_pipeline_status is invalid")
    reported_issues = data.get("issues", [])
    if not isinstance(reported_issues, Sequence) or isinstance(reported_issues, str):
        issues.append("issues must be a JSON array")
        reported_issues = []
    if int(data.get("issue_count") or 0) != len(list(reported_issues)):
        issues.append("issue_count must match issues length")
    plan = _coerce_mapping(data.get("fixture_execution_plan"))
    if plan.get("schema_version") != "source_adapter_fixture_execution_plan_v1":
        issues.append("fixture_execution_plan schema_version is invalid")
    if plan.get("source_adapter_fixture_pipeline_id") != pipeline_id:
        issues.append("fixture_execution_plan must reference source_adapter_fixture_pipeline_id")
    if plan.get("manual_or_live_actions_started") is not False or plan.get("live_network_default") is not False:
        issues.append("fixture_execution_plan must remain local and manual/live inactive")
    stage_rows = plan.get("stage_rows", [])
    if not isinstance(stage_rows, Sequence) or isinstance(stage_rows, str):
        issues.append("fixture_execution_plan.stage_rows must be a JSON array")
        stage_rows = []
    if int(data.get("planned_stage_count") or 0) != len(list(stage_rows)):
        issues.append("planned_stage_count must match execution plan stage rows")
    for index, row_raw in enumerate(stage_rows):
        row = _coerce_mapping(row_raw)
        if row.get("execution_mode") != "local_fixture_only":
            issues.append(f"stage row {index} must use local_fixture_only execution_mode")
        for basename in row.get("template_safe_basenames", []):
            if not _SAFE_BASENAME_RE.match(str(basename or "")):
                issues.append(f"stage row {index} contains unsafe template basename")
    assertions = _coerce_mapping(data.get("fixture_assertion_manifest"))
    if assertions.get("schema_version") != "source_adapter_fixture_assertion_manifest_v1":
        issues.append("fixture_assertion_manifest schema_version is invalid")
    if assertions.get("source_adapter_fixture_pipeline_id") != pipeline_id:
        issues.append("fixture_assertion_manifest must reference source_adapter_fixture_pipeline_id")
    assertion_rows = assertions.get("assertion_rows", [])
    if not isinstance(assertion_rows, Sequence) or isinstance(assertion_rows, str):
        issues.append("fixture_assertion_manifest.assertion_rows must be a JSON array")
        assertion_rows = []
    if int(data.get("fixture_count") or 0) != len(list(assertion_rows)):
        issues.append("fixture_count must match assertion manifest rows")
    handoff = _coerce_mapping(data.get("fixture_pipeline_closeout_handoff"))
    if handoff.get("schema_version") != "source_adapter_fixture_pipeline_closeout_handoff_v1":
        issues.append("fixture_pipeline_closeout_handoff schema_version is invalid")
    if handoff.get("source_adapter_fixture_pipeline_id") != pipeline_id:
        issues.append("fixture_pipeline_closeout_handoff must reference source_adapter_fixture_pipeline_id")
    summary = _coerce_mapping(data.get("operator_summary"))
    if summary.get("manual_or_live_actions_started") is not False or summary.get("live_network_default") is not False:
        issues.append("operator_summary must confirm local-only fixture behavior")
    return {
        "schema_version": _SCHEMA_VERSION,
        "source_adapter_fixture_pipeline_id": pipeline_id,
        "source_adapter_fixture_review_id": str(data.get("source_adapter_fixture_review_id") or ""),
        "fixture_pipeline_status": status,
        "fixture_count": int(data.get("fixture_count") or 0),
        "planned_stage_count": int(data.get("planned_stage_count") or 0),
        "issue_count": len(issues),
        "issues": issues,
        "verified": not issues,
    }


if __name__ == "__main__":
    from source_adapter_fixture_pipeline import build_source_adapter_fixture_pipeline

    package = build_source_adapter_fixture_pipeline(
        {
            "source_adapter_fixture_review_id": "source_adapter_fixture_review.example",
            "review_status": "PASSED",
            "adapter_reviews": [{"adapter_id": "article", "shared_pipeline_stages": ["artifact_collection"]}],
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
                    }
                ]
            },
        }
    )
    result = verify_source_adapter_fixture_pipeline(package)
    assert result["verified"], result
    print("Source Adapter Fixture Pipeline verifier self-test passed.")
