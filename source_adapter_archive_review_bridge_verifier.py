from __future__ import annotations

from typing import Any, Mapping

from source_archive_review_verifier import verify_source_archive_review

SCHEMA_VERSION = "source_adapter_archive_review_bridge_verifier_v1"


def _issue(issues: list[str], message: str) -> None:
    issues.append(message)


def verify_source_adapter_archive_review_bridge(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    pkg = dict(package or {})
    if pkg.get("schema_version") != "source_adapter_archive_review_bridge_v1":
        _issue(issues, "schema_version must be source_adapter_archive_review_bridge_v1")
    if pkg.get("archive_review_bridge_status") != "SHARED_ARCHIVE_REVIEWS_BUILT":
        _issue(issues, "archive_review_bridge_status must be SHARED_ARCHIVE_REVIEWS_BUILT")
    if not pkg.get("source_adapter_archive_review_bridge_id"):
        _issue(issues, "source_adapter_archive_review_bridge_id is required")
    if pkg.get("issue_count") not in (0, "0"):
        _issue(issues, "issue_count must be zero for verified archive review bridge output")

    outputs = pkg.get("archive_review_outputs")
    if not isinstance(outputs, list) or not outputs:
        _issue(issues, "archive_review_outputs must be a non-empty list")
    else:
        seen: set[str] = set()
        for index, output in enumerate(outputs):
            if not isinstance(output, Mapping):
                _issue(issues, f"archive_review_outputs[{index}] must be an object")
                continue
            review_package = output.get("archive_review_package")
            checklist = output.get("archive_review_checklist")
            decision = output.get("archive_review_decision")
            closeout = output.get("archive_review_closeout")
            if not isinstance(review_package, Mapping):
                _issue(issues, f"archive_review_outputs[{index}] missing archive_review_package")
                continue
            archive_review_package_id = str(review_package.get("archive_review_package_id") or "")
            if archive_review_package_id in seen:
                _issue(issues, f"duplicate archive_review_package_id: {archive_review_package_id}")
            seen.add(archive_review_package_id)
            verification = verify_source_archive_review(
                review_package,
                checklist if isinstance(checklist, Mapping) else None,
                decision if isinstance(decision, Mapping) else None,
                closeout if isinstance(closeout, Mapping) else None,
            )
            if not verification.get("verified"):
                _issue(issues, f"archive_review_outputs[{index}] failed shared verification: {verification.get('issues')}")

    batch = pkg.get("source_adapter_archive_review_batch")
    if not isinstance(batch, Mapping):
        _issue(issues, "source_adapter_archive_review_batch is required")
    else:
        if batch.get("schema_version") != "source_adapter_archive_review_batch_v1":
            _issue(issues, "source_adapter_archive_review_batch schema_version mismatch")
        if batch.get("archive_review_count") != len(outputs or []):
            _issue(issues, "source_adapter_archive_review_batch archive_review_count mismatch")
        if not isinstance(batch.get("archive_review_rows"), list) or not batch.get("archive_review_rows"):
            _issue(issues, "source_adapter_archive_review_batch must include archive_review_rows")

    handoff = pkg.get("source_adapter_pipeline_closeout_batch_handoff")
    if not isinstance(handoff, Mapping):
        _issue(issues, "source_adapter_pipeline_closeout_batch_handoff is required")
    else:
        if handoff.get("schema_version") != "source_adapter_pipeline_closeout_batch_handoff_v1":
            _issue(issues, "source_adapter_pipeline_closeout_batch_handoff schema_version mismatch")
        if handoff.get("handoff_status") != "READY_FOR_SHARED_PIPELINE_CLOSEOUT":
            _issue(issues, "pipeline closeout handoff must be READY_FOR_SHARED_PIPELINE_CLOSEOUT")
        if handoff.get("ready_for_pipeline_closeout") is not True:
            _issue(issues, "pipeline closeout handoff must be ready_for_pipeline_closeout")
        if handoff.get("required_next_stage") != "source_pipeline_closeout":
            _issue(issues, "pipeline closeout handoff required_next_stage must be source_pipeline_closeout")

    return {
        "schema_version": SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_archive_review_bridge_id": str(pkg.get("source_adapter_archive_review_bridge_id") or ""),
        "source_adapter_archive_result_intake_bridge_id": str(pkg.get("source_adapter_archive_result_intake_bridge_id") or ""),
        "archive_review_count": len(outputs) if isinstance(outputs, list) else 0,
        "handoff_status": str(handoff.get("handoff_status") if isinstance(handoff, Mapping) else ""),
    }
