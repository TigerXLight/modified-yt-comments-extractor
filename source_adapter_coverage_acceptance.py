from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "source_adapter_coverage_acceptance_v1"
PACKAGE_SCHEMA_VERSION = "source_adapter_coverage_acceptance_package_v1"
RECORD_SCHEMA_VERSION = "source_adapter_coverage_acceptance_record_v1"
REGISTRY_HANDOFF_SCHEMA_VERSION = "source_adapter_registry_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_coverage_acceptance_operator_summary_v1"

_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
_FORBIDDEN_PATH_FIELDS = {"path", "absolute_path", "local_path", "filesystem_path"}
_ALLOWED_CLOSEOUT_STATUSES = {
    "FIXTURE_PIPELINE_CLOSED",
    "READY_FOR_LOCAL_FIXTURE_RESULTS",
    "FIXTURE_PIPELINE_BLOCKED",
}
_ALLOWED_HANDOFF_STATUSES = {
    "READY_FOR_ADAPTER_COVERAGE_ACCEPTANCE",
    "WAITING_FOR_LOCAL_FIXTURE_RESULTS",
    "BLOCKED_BY_FIXTURE_PIPELINE",
    "",
}


class SourceAdapterCoverageAcceptanceError(ValueError):
    """Raised when adapter coverage acceptance input is invalid."""


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
        raise SourceAdapterCoverageAcceptanceError(f"{name} must be a JSON object")
    return dict(value)


def _coerce_sequence(value: object, *, name: str) -> list[Any]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise SourceAdapterCoverageAcceptanceError(f"{name} must be a JSON array")
    return list(value)


def _ensure_no_local_paths(value: Mapping[str, Any], *, name: str) -> None:
    present = sorted(_FORBIDDEN_PATH_FIELDS.intersection(value.keys()))
    if present:
        raise SourceAdapterCoverageAcceptanceError(f"{name} must not include local path fields: {', '.join(present)}")


def _assert_no_forbidden_keys(value: object, *, name: str) -> None:
    if isinstance(value, Mapping):
        _ensure_no_local_paths(value, name=name)
        for key, child in value.items():
            _assert_no_forbidden_keys(child, name=f"{name}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _assert_no_forbidden_keys(child, name=f"{name}[{index}]")


def _closeout_ids(closeout: Mapping[str, Any]) -> dict[str, str]:
    closeout_id = str(closeout.get("source_adapter_fixture_pipeline_closeout_id") or "").strip()
    if not closeout_id:
        raise SourceAdapterCoverageAcceptanceError("source_adapter_fixture_pipeline_closeout_id is required")
    pipeline_id = str(closeout.get("source_adapter_fixture_pipeline_id") or "").strip()
    if not pipeline_id:
        raise SourceAdapterCoverageAcceptanceError("source_adapter_fixture_pipeline_id is required")
    return {
        "source_adapter_fixture_pipeline_closeout_id": closeout_id,
        "source_adapter_fixture_pipeline_id": pipeline_id,
        "source_adapter_fixture_review_id": str(closeout.get("source_adapter_fixture_review_id") or ""),
        "source_adapter_fixture_authoring_id": str(closeout.get("source_adapter_fixture_authoring_id") or ""),
        "source_adapter_fixture_matrix_id": str(closeout.get("source_adapter_fixture_matrix_id") or ""),
    }


def _closeout_status(closeout: Mapping[str, Any]) -> str:
    status = str(closeout.get("closeout_status") or "").strip().upper()
    if status not in _ALLOWED_CLOSEOUT_STATUSES:
        raise SourceAdapterCoverageAcceptanceError(
            "closeout_status must be one of " + ", ".join(sorted(_ALLOWED_CLOSEOUT_STATUSES))
        )
    return status


def _handoff_status(closeout: Mapping[str, Any], handoff: Mapping[str, Any] | None) -> str:
    raw_handoff = handoff
    if raw_handoff is None:
        raw_handoff = _coerce_mapping(closeout.get("adapter_acceptance_handoff", {}), name="adapter_acceptance_handoff")
    status = str(raw_handoff.get("handoff_status") or "").strip().upper()
    if status not in _ALLOWED_HANDOFF_STATUSES:
        raise SourceAdapterCoverageAcceptanceError(
            "handoff_status must be one of " + ", ".join(sorted(_ALLOWED_HANDOFF_STATUSES - {""}))
        )
    return status


def _traceability(closeout: Mapping[str, Any], traceability_index: Mapping[str, Any] | None) -> dict[str, Any]:
    raw_traceability = traceability_index
    if raw_traceability is None:
        raw_traceability = _coerce_mapping(closeout.get("traceability_index", {}), name="traceability_index")
    traceability = _coerce_mapping(raw_traceability, name="traceability_index")
    _assert_no_forbidden_keys(traceability, name="traceability_index")
    adapters = sorted({_clean_identifier(adapter, fallback="adapter").lower() for adapter in traceability.get("adapters", [])})
    stage_rows: list[dict[str, Any]] = []
    for index, raw in enumerate(_coerce_sequence(traceability.get("stage_rows", []), name="traceability_index.stage_rows")):
        row = _coerce_mapping(raw, name=f"traceability_index.stage_rows[{index}]")
        stage_rows.append(
            {
                "adapter_id": _clean_identifier(row.get("adapter_id"), fallback=f"adapter_{index + 1}").lower(),
                "stage_id": _clean_identifier(row.get("stage_id"), fallback="stage").lower(),
                "execution_mode": str(row.get("execution_mode") or ""),
                "fixture_count": int(row.get("fixture_count") or 0),
            }
        )
    result_rows: list[dict[str, Any]] = []
    for index, raw in enumerate(_coerce_sequence(traceability.get("result_rows", []), name="traceability_index.result_rows")):
        row = _coerce_mapping(raw, name=f"traceability_index.result_rows[{index}]")
        result_rows.append(
            {
                "adapter_id": _clean_identifier(row.get("adapter_id"), fallback=f"adapter_{index + 1}").lower(),
                "stage_id": _clean_identifier(row.get("stage_id"), fallback="stage").lower(),
                "result_status": str(row.get("result_status") or "").strip().upper(),
                "issue_count": int(row.get("issue_count") or 0),
            }
        )
    if not adapters:
        adapters = sorted({row["adapter_id"] for row in stage_rows} | {row["adapter_id"] for row in result_rows})
    return {
        "adapter_ids": adapters,
        "stage_rows": stage_rows,
        "result_rows": result_rows,
        "fixture_count": int(traceability.get("fixture_count") or 0),
        "planned_stage_count": int(traceability.get("planned_stage_count") or len(stage_rows)),
        "result_count": int(traceability.get("result_count") or len(result_rows)),
    }


def _acceptance_status(closeout_status: str, handoff_status: str, issues: Sequence[str], traceability: Mapping[str, Any]) -> str:
    if issues:
        return "ADAPTER_COVERAGE_ACCEPTANCE_BLOCKED"
    if closeout_status == "FIXTURE_PIPELINE_CLOSED" and handoff_status == "READY_FOR_ADAPTER_COVERAGE_ACCEPTANCE":
        return "ADAPTER_COVERAGE_ACCEPTED"
    if closeout_status == "READY_FOR_LOCAL_FIXTURE_RESULTS" or handoff_status == "WAITING_FOR_LOCAL_FIXTURE_RESULTS":
        return "WAITING_FOR_LOCAL_FIXTURE_RESULTS"
    return "ADAPTER_COVERAGE_ACCEPTANCE_BLOCKED"


def build_source_adapter_coverage_acceptance(
    fixture_pipeline_closeout: Mapping[str, Any],
    traceability_index: Mapping[str, Any] | None = None,
    acceptance_handoff: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic local-only adapter coverage acceptance package."""

    closeout = _coerce_mapping(fixture_pipeline_closeout, name="fixture_pipeline_closeout")
    _assert_no_forbidden_keys(closeout, name="fixture_pipeline_closeout")
    ids = _closeout_ids(closeout)
    closeout_status = _closeout_status(closeout)
    handoff = _coerce_mapping(acceptance_handoff, name="acceptance_handoff") if acceptance_handoff is not None else None
    if handoff is not None:
        _assert_no_forbidden_keys(handoff, name="acceptance_handoff")
    handoff_status = _handoff_status(closeout, handoff)
    traceability = _traceability(closeout, traceability_index)

    issues: list[str] = [str(issue) for issue in closeout.get("issues", [])]
    closeout_issue_count = int(closeout.get("issue_count") or 0)
    if closeout_issue_count and not issues:
        issues.append("fixture pipeline closeout issue_count is non-zero but issues are empty")
    if handoff is not None:
        handoff_closeout_id = str(handoff.get("source_adapter_fixture_pipeline_closeout_id") or "")
        if handoff_closeout_id and handoff_closeout_id != ids["source_adapter_fixture_pipeline_closeout_id"]:
            issues.append("acceptance handoff does not match source_adapter_fixture_pipeline_closeout_id")
    if not traceability["adapter_ids"]:
        issues.append("traceability index does not contain adapters")
    if traceability["planned_stage_count"] != len(traceability["stage_rows"]):
        issues.append("planned_stage_count does not match traceability stage rows")
    if traceability["result_count"] != len(traceability["result_rows"]):
        issues.append("result_count does not match traceability result rows")
    failing_results = [row for row in traceability["result_rows"] if row["result_status"] not in {"PASS", "PASSED"}]
    if closeout_status == "FIXTURE_PIPELINE_CLOSED" and failing_results:
        issues.append("closed fixture pipeline contains non-passing result rows")

    status = _acceptance_status(closeout_status, handoff_status, issues, traceability)
    accepted = status == "ADAPTER_COVERAGE_ACCEPTED"
    base = {
        **ids,
        "closeout_status": closeout_status,
        "handoff_status": handoff_status,
        "adapter_count": len(traceability["adapter_ids"]),
        "fixture_count": traceability["fixture_count"],
        "planned_stage_count": traceability["planned_stage_count"],
        "result_count": traceability["result_count"],
        "issue_count": len(issues),
    }
    acceptance_id = f"source_adapter_coverage_acceptance.{_stable_hash(base)}"
    acceptance_record = {
        "schema_version": RECORD_SCHEMA_VERSION,
        "source_adapter_coverage_acceptance_id": acceptance_id,
        **ids,
        "acceptance_status": status,
        "closeout_status": closeout_status,
        "handoff_status": handoff_status,
        "adapter_count": len(traceability["adapter_ids"]),
        "accepted_adapter_count": len(traceability["adapter_ids"]) if accepted else 0,
        "fixture_count": traceability["fixture_count"],
        "planned_stage_count": traceability["planned_stage_count"],
        "result_count": traceability["result_count"],
        "issue_count": len(issues),
        "issues": issues,
        "manual_or_live_actions_started": False,
        "live_network_default": False,
    }
    registry_handoff = {
        "schema_version": REGISTRY_HANDOFF_SCHEMA_VERSION,
        "source_adapter_coverage_acceptance_id": acceptance_id,
        "source_adapter_fixture_pipeline_closeout_id": ids["source_adapter_fixture_pipeline_closeout_id"],
        "handoff_status": "READY_FOR_ADAPTER_REGISTRY_UPDATE" if accepted else status,
        "adapters": [
            {
                "adapter_id": adapter_id,
                "coverage_status": "ACCEPTED_SHARED_FIXTURE_COVERAGE" if accepted else "NOT_ACCEPTED",
                "shared_stage_coverage": [
                    row["stage_id"] for row in traceability["stage_rows"] if row["adapter_id"] == adapter_id
                ],
                "accepted_for_shared_pipeline": accepted,
            }
            for adapter_id in traceability["adapter_ids"]
        ],
        "manual_or_live_actions_started": False,
        "live_network_default": False,
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "source_adapter_coverage_acceptance_id": acceptance_id,
        "acceptance_status": status,
        "adapter_count": len(traceability["adapter_ids"]),
        "accepted_adapter_count": len(traceability["adapter_ids"]) if accepted else 0,
        "fixture_count": traceability["fixture_count"],
        "issue_count": len(issues),
        "manual_or_live_actions_started": False,
        "live_network_default": False,
        "next_actions": [
            "Use accepted adapter coverage handoffs to update the adapter registry in a separate explicit step.",
            "Keep blocked or waiting fixture pipelines out of adapter registration acceptance.",
            "Continue adding adapters as specs plus shared-stage fixture coverage, not cloned website pipelines.",
        ],
    }
    return {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "source_adapter_coverage_acceptance_id": acceptance_id,
        **ids,
        "acceptance_status": status,
        "closeout_status": closeout_status,
        "handoff_status": handoff_status,
        "adapter_count": len(traceability["adapter_ids"]),
        "accepted_adapter_count": len(traceability["adapter_ids"]) if accepted else 0,
        "fixture_count": traceability["fixture_count"],
        "planned_stage_count": traceability["planned_stage_count"],
        "result_count": traceability["result_count"],
        "issue_count": len(issues),
        "issues": issues,
        "acceptance_record": acceptance_record,
        "adapter_registry_handoff": registry_handoff,
        "operator_summary": operator_summary,
    }


def load_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise SourceAdapterCoverageAcceptanceError("JSON input must be an object")
    return dict(data)


def write_json_file(path: str | Path, data: Mapping[str, Any]) -> None:
    Path(path).write_bytes(_json_bytes(data))


if __name__ == "__main__":
    closeout = {
        "source_adapter_fixture_pipeline_closeout_id": "source_adapter_fixture_pipeline_closeout.example",
        "source_adapter_fixture_pipeline_id": "source_adapter_fixture_pipeline.example",
        "source_adapter_fixture_review_id": "source_adapter_fixture_review.example",
        "closeout_status": "FIXTURE_PIPELINE_CLOSED",
        "issue_count": 0,
        "issues": [],
        "traceability_index": {
            "adapters": ["article"],
            "fixture_count": 1,
            "planned_stage_count": 1,
            "result_count": 1,
            "stage_rows": [{"adapter_id": "article", "stage_id": "content_extraction", "fixture_count": 1}],
            "result_rows": [{"adapter_id": "article", "stage_id": "content_extraction", "result_status": "PASS", "issue_count": 0}],
        },
        "adapter_acceptance_handoff": {"handoff_status": "READY_FOR_ADAPTER_COVERAGE_ACCEPTANCE"},
    }
    result = build_source_adapter_coverage_acceptance(closeout)
    assert result["acceptance_status"] == "ADAPTER_COVERAGE_ACCEPTED", result
    print("Source Adapter Coverage Acceptance self-test passed.")
