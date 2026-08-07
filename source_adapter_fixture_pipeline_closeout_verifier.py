from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

_SCHEMA_VERSION = "source_adapter_fixture_pipeline_closeout_verifier_v1"
_REQUIRED_TOP_LEVEL = {
    "schema_version",
    "source_adapter_fixture_pipeline_closeout_id",
    "source_adapter_fixture_pipeline_id",
    "fixture_pipeline_status",
    "closeout_status",
    "adapter_count",
    "fixture_count",
    "planned_stage_count",
    "result_count",
    "issue_count",
    "issues",
    "closeout_record",
    "traceability_index",
    "adapter_acceptance_handoff",
    "operator_summary",
}
_ALLOWED_CLOSEOUT_STATUSES = {"FIXTURE_PIPELINE_CLOSED", "READY_FOR_LOCAL_FIXTURE_RESULTS", "FIXTURE_PIPELINE_BLOCKED"}
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


def verify_source_adapter_fixture_pipeline_closeout(package: Mapping[str, Any]) -> dict[str, Any]:
    data = dict(package) if isinstance(package, Mapping) else {}
    issues: list[str] = []
    missing = sorted(_REQUIRED_TOP_LEVEL - data.keys())
    if missing:
        issues.append("missing required fields: " + ", ".join(missing))
    _collect_forbidden_path_fields(data, issues=issues)
    closeout_id = str(data.get("source_adapter_fixture_pipeline_closeout_id") or "")
    pipeline_id = str(data.get("source_adapter_fixture_pipeline_id") or "")
    closeout_status = str(data.get("closeout_status") or "")
    pipeline_status = str(data.get("fixture_pipeline_status") or "")
    if data.get("schema_version") != "source_adapter_fixture_pipeline_closeout_package_v1":
        issues.append("schema_version is invalid")
    if not closeout_id:
        issues.append("source_adapter_fixture_pipeline_closeout_id is required")
    if not pipeline_id:
        issues.append("source_adapter_fixture_pipeline_id is required")
    if closeout_status not in _ALLOWED_CLOSEOUT_STATUSES:
        issues.append("closeout_status is invalid")
    package_issue_count = int(data.get("issue_count") or 0)
    package_issues = data.get("issues", [])
    if not isinstance(package_issues, Sequence) or isinstance(package_issues, str):
        issues.append("issues must be a JSON array")
        package_issues = []
    if package_issue_count != len(list(package_issues)):
        issues.append("issue_count must match issues length")
    record = _coerce_mapping(data.get("closeout_record"))
    if record.get("schema_version") != "source_adapter_fixture_pipeline_closeout_record_v1":
        issues.append("closeout_record schema_version is invalid")
    if record.get("source_adapter_fixture_pipeline_closeout_id") != closeout_id:
        issues.append("closeout_record must reference closeout id")
    if record.get("manual_or_live_actions_started") is not False or record.get("live_network_default") is not False:
        issues.append("closeout_record must remain local-only")
    traceability = _coerce_mapping(data.get("traceability_index"))
    if traceability.get("schema_version") != "source_adapter_fixture_pipeline_traceability_index_v1":
        issues.append("traceability_index schema_version is invalid")
    if traceability.get("source_adapter_fixture_pipeline_closeout_id") != closeout_id:
        issues.append("traceability_index must reference closeout id")
    stage_rows = traceability.get("stage_rows", [])
    assertion_rows = traceability.get("assertion_rows", [])
    result_rows = traceability.get("result_rows", [])
    if not isinstance(stage_rows, Sequence) or isinstance(stage_rows, str):
        issues.append("traceability_index.stage_rows must be a JSON array")
        stage_rows = []
    if not isinstance(assertion_rows, Sequence) or isinstance(assertion_rows, str):
        issues.append("traceability_index.assertion_rows must be a JSON array")
        assertion_rows = []
    if not isinstance(result_rows, Sequence) or isinstance(result_rows, str):
        issues.append("traceability_index.result_rows must be a JSON array")
        result_rows = []
    if int(data.get("planned_stage_count") or 0) != len(list(stage_rows)):
        issues.append("planned_stage_count must match traceability stage rows")
    if int(data.get("fixture_count") or 0) != len(list(assertion_rows)):
        issues.append("fixture_count must match traceability assertion rows")
    if int(data.get("result_count") or 0) != len(list(result_rows)):
        issues.append("result_count must match traceability result rows")
    for index, row_raw in enumerate(assertion_rows):
        row = _coerce_mapping(row_raw)
        basename = str(row.get("template_safe_basename") or "")
        if basename and not _SAFE_BASENAME_RE.match(basename):
            issues.append(f"assertion row {index} contains unsafe template basename")
    handoff = _coerce_mapping(data.get("adapter_acceptance_handoff"))
    if handoff.get("schema_version") != "source_adapter_fixture_acceptance_handoff_v1":
        issues.append("adapter_acceptance_handoff schema_version is invalid")
    if handoff.get("source_adapter_fixture_pipeline_closeout_id") != closeout_id:
        issues.append("adapter_acceptance_handoff must reference closeout id")
    if handoff.get("manual_or_live_actions_started") is not False or handoff.get("live_network_default") is not False:
        issues.append("adapter_acceptance_handoff must remain local-only")
    if closeout_status == "FIXTURE_PIPELINE_CLOSED" and pipeline_status != "PASSED":
        issues.append("closed fixture pipelines must have PASSED fixture_pipeline_status")
    if closeout_status == "FIXTURE_PIPELINE_CLOSED" and package_issue_count != 0:
        issues.append("closed fixture pipelines must not carry issues")
    summary = _coerce_mapping(data.get("operator_summary"))
    if summary.get("manual_or_live_actions_started") is not False or summary.get("live_network_default") is not False:
        issues.append("operator_summary must confirm local-only behavior")
    return {
        "schema_version": _SCHEMA_VERSION,
        "source_adapter_fixture_pipeline_closeout_id": closeout_id,
        "source_adapter_fixture_pipeline_id": pipeline_id,
        "closeout_status": closeout_status,
        "fixture_pipeline_status": pipeline_status,
        "adapter_count": int(data.get("adapter_count") or 0),
        "fixture_count": int(data.get("fixture_count") or 0),
        "issue_count": len(issues),
        "issues": issues,
        "verified": not issues,
    }


if __name__ == "__main__":
    from source_adapter_fixture_pipeline_closeout import build_source_adapter_fixture_pipeline_closeout

    package = build_source_adapter_fixture_pipeline_closeout(
        {
            "source_adapter_fixture_pipeline_id": "source_adapter_fixture_pipeline.example",
            "fixture_pipeline_status": "PASSED",
            "fixture_count": 1,
            "planned_stage_count": 1,
            "result_count": 1,
            "issue_count": 0,
            "issues": [],
            "fixture_execution_plan": {"stage_rows": [{"adapter_id": "article", "stage_id": "content_extraction", "execution_mode": "local_fixture_only", "fixture_count": 1, "fixture_types": ["expected_content_extraction_json"], "template_safe_basenames": ["article.expected.json"]}]},
            "fixture_assertion_manifest": {"assertion_rows": [{"adapter_id": "article", "fixture_type": "expected_content_extraction_json", "template_safe_basename": "article.expected.json"}]},
            "stage_results": [{"adapter_id": "article", "stage_id": "content_extraction", "result_status": "PASS", "issue_count": 0, "issues": []}],
        }
    )
    result = verify_source_adapter_fixture_pipeline_closeout(package)
    assert result["verified"], result
    print("Source Adapter Fixture Pipeline Closeout verifier self-test passed.")
