from __future__ import annotations

from typing import Any, Mapping

from source_archive_result_intake_verifier import verify_source_archive_result_intake

SCHEMA_VERSION = "source_adapter_archive_result_intake_bridge_verifier_v1"


def _issue(issues: list[str], message: str) -> None:
    issues.append(message)


def verify_source_adapter_archive_result_intake_bridge(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    pkg = dict(package or {})
    if pkg.get("schema_version") != "source_adapter_archive_result_intake_bridge_v1":
        _issue(issues, "schema_version must be source_adapter_archive_result_intake_bridge_v1")
    if pkg.get("archive_result_intake_bridge_status") != "SHARED_ARCHIVE_RESULT_INTAKES_BUILT":
        _issue(issues, "archive_result_intake_bridge_status must be SHARED_ARCHIVE_RESULT_INTAKES_BUILT")
    if not pkg.get("source_adapter_archive_result_intake_bridge_id"):
        _issue(issues, "source_adapter_archive_result_intake_bridge_id is required")
    if pkg.get("issue_count") not in (0, "0"):
        _issue(issues, "issue_count must be zero for verified archive result intake bridge output")

    outputs = pkg.get("archive_result_intake_outputs")
    if not isinstance(outputs, list) or not outputs:
        _issue(issues, "archive_result_intake_outputs must be a non-empty list")
    else:
        seen: set[str] = set()
        for index, output in enumerate(outputs):
            if not isinstance(output, Mapping):
                _issue(issues, f"archive_result_intake_outputs[{index}] must be an object")
                continue
            record = output.get("archive_result_intake_record")
            receipt_index = output.get("archive_receipt_index")
            review_handoff = output.get("archive_review_handoff")
            if not isinstance(record, Mapping):
                _issue(issues, f"archive_result_intake_outputs[{index}] missing archive_result_intake_record")
                continue
            archive_result_intake_id = str(record.get("archive_result_intake_id") or "")
            if archive_result_intake_id in seen:
                _issue(issues, f"duplicate archive_result_intake_id: {archive_result_intake_id}")
            seen.add(archive_result_intake_id)
            verification = verify_source_archive_result_intake(
                record,
                receipt_index if isinstance(receipt_index, Mapping) else None,
                review_handoff if isinstance(review_handoff, Mapping) else None,
            )
            if not verification.get("verified"):
                _issue(issues, f"archive_result_intake_outputs[{index}] failed shared verification: {verification.get('issues')}")

    batch = pkg.get("source_adapter_archive_result_intake_batch")
    if not isinstance(batch, Mapping):
        _issue(issues, "source_adapter_archive_result_intake_batch is required")
    else:
        if batch.get("schema_version") != "source_adapter_archive_result_intake_batch_v1":
            _issue(issues, "source_adapter_archive_result_intake_batch schema_version mismatch")
        if batch.get("archive_result_intake_count") != len(outputs or []):
            _issue(issues, "source_adapter_archive_result_intake_batch archive_result_intake_count mismatch")
        if not isinstance(batch.get("archive_result_intake_rows"), list) or not batch.get("archive_result_intake_rows"):
            _issue(issues, "source_adapter_archive_result_intake_batch must include archive_result_intake_rows")

    handoff = pkg.get("source_adapter_archive_review_batch_handoff")
    if not isinstance(handoff, Mapping):
        _issue(issues, "source_adapter_archive_review_batch_handoff is required")
    else:
        if handoff.get("schema_version") != "source_adapter_archive_review_batch_handoff_v1":
            _issue(issues, "source_adapter_archive_review_batch_handoff schema_version mismatch")
        if handoff.get("handoff_status") != "READY_FOR_SHARED_ARCHIVE_REVIEW":
            _issue(issues, "archive review batch must be READY_FOR_SHARED_ARCHIVE_REVIEW")
        if handoff.get("ready_for_archive_review") is not True:
            _issue(issues, "archive review batch must be ready_for_archive_review")
        if handoff.get("required_next_stage") != "source_archive_review":
            _issue(issues, "archive review batch required_next_stage must be source_archive_review")

    return {
        "schema_version": SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_archive_result_intake_bridge_id": str(pkg.get("source_adapter_archive_result_intake_bridge_id") or ""),
        "source_adapter_archive_handoff_bridge_id": str(pkg.get("source_adapter_archive_handoff_bridge_id") or ""),
        "archive_result_intake_count": len(outputs) if isinstance(outputs, list) else 0,
        "handoff_status": str(handoff.get("handoff_status") if isinstance(handoff, Mapping) else ""),
    }
