from __future__ import annotations

from typing import Any, Mapping

SCHEMA_VERSION = "source_evidence_review_verifier_v1"
_ALLOWED_DECISIONS = {"PENDING_DECISION", "APPROVED", "REJECTED", "REVISION_REQUESTED"}


def verify_source_evidence_review(
    evidence_review_package: Mapping[str, Any],
    evidence_review_decision: Mapping[str, Any] | None = None,
    release_handoff: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    issues: list[str] = []
    package = evidence_review_package if isinstance(evidence_review_package, Mapping) else {}
    decision_record = evidence_review_decision if isinstance(evidence_review_decision, Mapping) else {}
    handoff = release_handoff if isinstance(release_handoff, Mapping) else {}

    review_package_id = str(package.get("evidence_review_package_id") or "")
    queue_item_id = str(package.get("queue_item_id") or "")

    if package.get("schema_version") != "source_evidence_review_v1":
        issues.append("evidence_review_package.schema_version must be source_evidence_review_v1")
    if not review_package_id:
        issues.append("evidence_review_package_id is required")
    if not queue_item_id:
        issues.append("queue_item_id is required")
    if not str(package.get("total_export_package_id") or ""):
        issues.append("total_export_package_id is required")
    if not str(package.get("capture_bundle_id") or ""):
        issues.append("capture_bundle_id is required")
    if not str(package.get("adapter_id") or ""):
        issues.append("adapter_id is required")
    if package.get("review_package_status") != "READY_FOR_REVIEW_DECISION":
        issues.append("review_package_status must be READY_FOR_REVIEW_DECISION")

    required_actions = package.get("required_review_actions")
    if not isinstance(required_actions, list) or not required_actions:
        issues.append("required_review_actions must be a non-empty list")

    artifact_index = package.get("artifact_index")
    if not isinstance(artifact_index, list):
        issues.append("artifact_index must be a list")
    else:
        for index, artifact in enumerate(artifact_index):
            if not isinstance(artifact, Mapping):
                issues.append(f"artifact_index[{index}] must be an object")
                continue
            filename = str(artifact.get("filename") or "")
            if any(sep in filename for sep in ("/", "\\")) or (len(filename) > 1 and filename[1] == ":"):
                issues.append(f"artifact_index[{index}].filename must be a basename")

    decision = str(decision_record.get("decision") or "") if decision_record else ""
    if decision_record:
        if decision_record.get("schema_version") != "source_evidence_review_decision_v1":
            issues.append("evidence_review_decision.schema_version must be source_evidence_review_decision_v1")
        if str(decision_record.get("evidence_review_package_id") or "") != review_package_id:
            issues.append("evidence_review_decision.evidence_review_package_id mismatch")
        if decision not in _ALLOWED_DECISIONS:
            issues.append("evidence_review_decision.decision is invalid")
        if not str(decision_record.get("reviewer_id") or ""):
            issues.append("evidence_review_decision.reviewer_id is required")
        missing = decision_record.get("missing_required_action_ids")
        if decision != "PENDING_DECISION" and missing:
            issues.append("completed_action_ids must include all required review actions before final decision")
        if decision == "APPROVED" and decision_record.get("approved_for_release") is not True:
            issues.append("APPROVED decision must set approved_for_release true")

    if handoff:
        if handoff.get("schema_version") != "source_evidence_review_release_handoff_v1":
            issues.append("release_handoff.schema_version must be source_evidence_review_release_handoff_v1")
        if str(handoff.get("evidence_review_package_id") or "") != review_package_id:
            issues.append("release_handoff.evidence_review_package_id mismatch")
        handoff_status = str(handoff.get("handoff_status") or "")
        if decision == "APPROVED" and handoff_status != "READY_FOR_APPROVED_RELEASE":
            issues.append("APPROVED decision must produce READY_FOR_APPROVED_RELEASE handoff")
        if decision in {"REJECTED", "REVISION_REQUESTED", "PENDING_DECISION"} and handoff_status == "READY_FOR_APPROVED_RELEASE":
            issues.append("non-approved decision cannot produce READY_FOR_APPROVED_RELEASE handoff")

    return {
        "schema_version": SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "evidence_review_package_id": review_package_id,
        "queue_item_id": queue_item_id,
        "decision": decision,
        "adapter_id": str(package.get("adapter_id") or ""),
        "source_url": str(package.get("source_url") or ""),
    }
