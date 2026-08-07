from __future__ import annotations

from typing import Any, Mapping

from source_pipeline_closeout_verifier import verify_source_pipeline_closeout

SCHEMA_VERSION = "source_adapter_pipeline_closeout_bridge_verifier_v1"


def _issue(issues: list[str], message: str) -> None:
    issues.append(message)


def verify_source_adapter_pipeline_closeout_bridge(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    pkg = dict(package or {})
    if pkg.get("schema_version") != "source_adapter_pipeline_closeout_bridge_v1":
        _issue(issues, "schema_version must be source_adapter_pipeline_closeout_bridge_v1")
    if pkg.get("pipeline_closeout_bridge_status") != "SHARED_PIPELINE_CLOSEOUTS_BUILT":
        _issue(issues, "pipeline_closeout_bridge_status must be SHARED_PIPELINE_CLOSEOUTS_BUILT")
    if not pkg.get("source_adapter_pipeline_closeout_bridge_id"):
        _issue(issues, "source_adapter_pipeline_closeout_bridge_id is required")
    if pkg.get("issue_count") not in (0, "0"):
        _issue(issues, "issue_count must be zero for verified pipeline closeout bridge output")

    outputs = pkg.get("pipeline_closeout_outputs")
    if not isinstance(outputs, list) or not outputs:
        _issue(issues, "pipeline_closeout_outputs must be a non-empty list")
    else:
        seen: set[str] = set()
        for index, output in enumerate(outputs):
            if not isinstance(output, Mapping):
                _issue(issues, f"pipeline_closeout_outputs[{index}] must be an object")
                continue
            report = output.get("closeout_report")
            if not isinstance(report, Mapping):
                _issue(issues, f"pipeline_closeout_outputs[{index}] missing closeout_report")
                continue
            closeout_id = str(report.get("source_pipeline_closeout_id") or "")
            if closeout_id in seen:
                _issue(issues, f"duplicate source_pipeline_closeout_id: {closeout_id}")
            seen.add(closeout_id)
            verification = verify_source_pipeline_closeout(output)
            if not verification.get("verified"):
                _issue(issues, f"pipeline_closeout_outputs[{index}] failed shared verification: {verification.get('issues')}")
            if report.get("final_status") != "SOURCE_PIPELINE_COMPLETE":
                _issue(issues, f"pipeline_closeout_outputs[{index}] final_status must be SOURCE_PIPELINE_COMPLETE")

    batch = pkg.get("source_adapter_pipeline_closeout_batch")
    if not isinstance(batch, Mapping):
        _issue(issues, "source_adapter_pipeline_closeout_batch is required")
    else:
        if batch.get("schema_version") != "source_adapter_pipeline_closeout_batch_v1":
            _issue(issues, "source_adapter_pipeline_closeout_batch schema_version mismatch")
        if batch.get("pipeline_closeout_count") != len(outputs or []):
            _issue(issues, "source_adapter_pipeline_closeout_batch pipeline_closeout_count mismatch")
        if not isinstance(batch.get("pipeline_closeout_rows"), list) or not batch.get("pipeline_closeout_rows"):
            _issue(issues, "source_adapter_pipeline_closeout_batch must include pipeline_closeout_rows")
        if batch.get("complete_count") != len(outputs or []):
            _issue(issues, "source_adapter_pipeline_closeout_batch complete_count must match output count")

    handoff = pkg.get("source_adapter_shared_pipeline_roadmap_closeout_handoff")
    if not isinstance(handoff, Mapping):
        _issue(issues, "source_adapter_shared_pipeline_roadmap_closeout_handoff is required")
    else:
        if handoff.get("schema_version") != "source_adapter_shared_pipeline_roadmap_closeout_handoff_v1":
            _issue(issues, "roadmap closeout handoff schema_version mismatch")
        if handoff.get("handoff_status") != "SOURCE_ADAPTER_SHARED_PIPELINE_COMPLETE":
            _issue(issues, "roadmap closeout handoff must be SOURCE_ADAPTER_SHARED_PIPELINE_COMPLETE")
        if handoff.get("shared_pipeline_complete") is not True:
            _issue(issues, "roadmap closeout handoff must mark shared_pipeline_complete")
        if handoff.get("required_next_stage") != "source_adapter_runtime_wiring_or_fixture_expansion":
            _issue(issues, "roadmap closeout handoff required_next_stage mismatch")

    return {
        "schema_version": SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_pipeline_closeout_bridge_id": str(pkg.get("source_adapter_pipeline_closeout_bridge_id") or ""),
        "source_adapter_archive_review_bridge_id": str(pkg.get("source_adapter_archive_review_bridge_id") or ""),
        "pipeline_closeout_count": len(outputs) if isinstance(outputs, list) else 0,
        "handoff_status": str(handoff.get("handoff_status") if isinstance(handoff, Mapping) else ""),
    }
