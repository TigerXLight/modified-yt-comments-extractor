from __future__ import annotations

from typing import Any, Mapping

SCHEMA_VERSION = "source_adapter_evidence_queue_bridge_verifier_v1"


def _issue(issues: list[str], condition: bool, message: str) -> None:
    if not condition:
        issues.append(message)


def verify_source_adapter_evidence_queue_bridge(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if not isinstance(package, Mapping):
        return {
            "schema_version": SCHEMA_VERSION,
            "verified": False,
            "issue_count": 1,
            "issues": ["package must be a JSON object"],
            "source_adapter_evidence_queue_bridge_id": "",
        }

    bridge_id = str(package.get("source_adapter_evidence_queue_bridge_id") or "")
    _issue(issues, package.get("schema_version") == "source_adapter_evidence_queue_bridge_v1", "schema_version mismatch")
    _issue(issues, bool(bridge_id), "source_adapter_evidence_queue_bridge_id is required")
    _issue(issues, package.get("evidence_queue_bridge_status") == "SHARED_EVIDENCE_QUEUE_ITEMS_BUILT", "evidence_queue_bridge_status must be SHARED_EVIDENCE_QUEUE_ITEMS_BUILT")

    outputs = package.get("evidence_queue_outputs")
    if not isinstance(outputs, list) or not outputs:
        issues.append("evidence_queue_outputs must be a non-empty list")
        outputs = []
    queue_ids: list[str] = []
    for idx, output in enumerate(outputs):
        if not isinstance(output, Mapping):
            issues.append(f"evidence_queue_outputs[{idx}] must be an object")
            continue
        item = output.get("evidence_queue_item")
        index = output.get("evidence_queue_index")
        handoff = output.get("evidence_review_handoff")
        if not isinstance(item, Mapping):
            issues.append(f"evidence_queue_outputs[{idx}].evidence_queue_item is required")
            continue
        queue_id = str(item.get("queue_item_id") or "")
        queue_ids.append(queue_id)
        if item.get("schema_version") != "source_evidence_queue_v1":
            issues.append(f"evidence_queue_outputs[{idx}].evidence_queue_item schema mismatch")
        if not queue_id:
            issues.append(f"evidence_queue_outputs[{idx}].queue_item_id is required")
        if item.get("queue_status") != "READY_FOR_EVIDENCE_REVIEW":
            issues.append(f"evidence_queue_outputs[{idx}].queue_status must be READY_FOR_EVIDENCE_REVIEW")
        if not isinstance(index, Mapping) or index.get("queue_item_count") != 1:
            issues.append(f"evidence_queue_outputs[{idx}].evidence_queue_index mismatch")
        if not isinstance(handoff, Mapping) or handoff.get("handoff_status") != "READY_FOR_EVIDENCE_REVIEW":
            issues.append(f"evidence_queue_outputs[{idx}].evidence_review_handoff must be READY_FOR_EVIDENCE_REVIEW")

    batch = package.get("source_adapter_evidence_queue_batch")
    if not isinstance(batch, Mapping):
        issues.append("source_adapter_evidence_queue_batch is required")
    else:
        if batch.get("schema_version") != "source_adapter_evidence_queue_batch_v1":
            issues.append("source_adapter_evidence_queue_batch schema mismatch")
        if int(batch.get("queue_item_count") or -1) != len(outputs):
            issues.append("source_adapter_evidence_queue_batch count mismatch")

    handoff = package.get("source_adapter_evidence_review_batch_handoff")
    if not isinstance(handoff, Mapping):
        issues.append("source_adapter_evidence_review_batch_handoff is required")
    else:
        if handoff.get("handoff_status") != "READY_FOR_SHARED_EVIDENCE_REVIEW":
            issues.append("source_adapter_evidence_review_batch_handoff status mismatch")
        listed = [str(item) for item in handoff.get("queue_item_ids", [])] if isinstance(handoff.get("queue_item_ids"), list) else []
        if listed != queue_ids:
            issues.append("source_adapter_evidence_review_batch_handoff queue_item_ids mismatch")

    return {
        "schema_version": SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_evidence_queue_bridge_id": bridge_id,
        "source_adapter_total_export_bridge_id": str(package.get("source_adapter_total_export_bridge_id") or ""),
        "queue_item_count": len(outputs),
    }
