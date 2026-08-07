from __future__ import annotations

from typing import Any, Mapping

VERIFIER_SCHEMA_VERSION = "source_adapter_evidence_review_bridge_verifier_v1"


def verify_source_adapter_evidence_review_bridge(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if package.get("schema_version") != "source_adapter_evidence_review_bridge_v1":
        issues.append("schema_version must be source_adapter_evidence_review_bridge_v1")
    if package.get("evidence_review_bridge_status") != "SHARED_EVIDENCE_REVIEWS_BUILT":
        issues.append("evidence_review_bridge_status must be SHARED_EVIDENCE_REVIEWS_BUILT")
    outputs = package.get("evidence_review_outputs")
    if not isinstance(outputs, list) or not outputs:
        issues.append("evidence_review_outputs must be a non-empty list")
    else:
        review_ids: set[str] = set()
        for index, output in enumerate(outputs):
            if not isinstance(output, Mapping):
                issues.append(f"evidence_review_outputs[{index}] must be a mapping")
                continue
            review_package = output.get("evidence_review_package")
            decision = output.get("evidence_review_decision")
            handoff = output.get("release_handoff")
            if not isinstance(review_package, Mapping):
                issues.append(f"evidence_review_outputs[{index}].evidence_review_package missing")
                continue
            review_id = str(review_package.get("evidence_review_package_id") or "")
            if not review_id:
                issues.append(f"evidence_review_outputs[{index}] missing evidence_review_package_id")
            elif review_id in review_ids:
                issues.append(f"duplicate evidence_review_package_id: {review_id}")
            review_ids.add(review_id)
            if not isinstance(decision, Mapping) or decision.get("schema_version") != "source_evidence_review_decision_v1":
                issues.append(f"evidence_review_outputs[{index}].evidence_review_decision schema mismatch")
            if not isinstance(handoff, Mapping) or handoff.get("schema_version") != "source_evidence_review_release_handoff_v1":
                issues.append(f"evidence_review_outputs[{index}].release_handoff schema mismatch")
    batch = package.get("source_adapter_evidence_review_batch")
    if not isinstance(batch, Mapping) or batch.get("schema_version") != "source_adapter_evidence_review_batch_v1":
        issues.append("source_adapter_evidence_review_batch schema mismatch")
    approved_handoff = package.get("source_adapter_approved_release_batch_handoff")
    if not isinstance(approved_handoff, Mapping) or approved_handoff.get("schema_version") != "source_adapter_approved_release_batch_handoff_v1":
        issues.append("source_adapter_approved_release_batch_handoff schema mismatch")
    if package.get("issue_count", 0) != 0:
        issues.append("package contains embedded issues")
    return {
        "schema_version": VERIFIER_SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_evidence_review_bridge_id": package.get("source_adapter_evidence_review_bridge_id", ""),
        "source_adapter_evidence_queue_bridge_id": package.get("source_adapter_evidence_queue_bridge_id", ""),
        "evidence_review_count": package.get("evidence_review_count", 0),
        "handoff_status": approved_handoff.get("handoff_status", "") if isinstance(approved_handoff, Mapping) else "",
    }
