from __future__ import annotations

from typing import Any, Mapping

SCHEMA_VERSION = "source_adapter_runtime_receipt_review_bridge_verifier_v1"


def _issue(issues: list[str], message: str) -> None:
    issues.append(message)


def verify_source_adapter_runtime_receipt_review_bridge(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    pkg = dict(package or {})
    if pkg.get("schema_version") != "source_adapter_runtime_receipt_review_bridge_v1":
        _issue(issues, "schema_version must be source_adapter_runtime_receipt_review_bridge_v1")
    if pkg.get("runtime_receipt_review_status") != "SOURCE_ADAPTER_RUNTIME_RECEIPTS_REVIEWED":
        _issue(issues, "runtime_receipt_review_status must be SOURCE_ADAPTER_RUNTIME_RECEIPTS_REVIEWED")
    bridge_id = str(pkg.get("source_adapter_runtime_receipt_review_bridge_id") or "")
    if not bridge_id:
        _issue(issues, "source_adapter_runtime_receipt_review_bridge_id is required")
    wiring_id = str(pkg.get("source_adapter_runtime_wiring_bridge_id") or "")
    if not wiring_id:
        _issue(issues, "source_adapter_runtime_wiring_bridge_id is required")
    if pkg.get("issue_count") not in (0, "0"):
        _issue(issues, "issue_count must be zero for verified runtime receipt review bridge output")

    batch = pkg.get("source_adapter_runtime_receipt_review_batch")
    if not isinstance(batch, Mapping):
        _issue(issues, "source_adapter_runtime_receipt_review_batch is required")
        rows = []
    else:
        if batch.get("schema_version") != "source_adapter_runtime_receipt_review_batch_v1":
            _issue(issues, "receipt review batch schema_version mismatch")
        rows = batch.get("review_rows")
        if not isinstance(rows, list) or not rows:
            _issue(issues, "receipt review batch must contain review_rows")
            rows = []
        if batch.get("runtime_receipt_review_count") != len(rows):
            _issue(issues, "runtime receipt review count mismatch")

    seen_actions: set[str] = set()
    accepted_rows = 0
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            _issue(issues, f"review_rows[{index}] must be an object")
            continue
        action_id = str(row.get("runtime_action_id") or "")
        if not action_id:
            _issue(issues, f"review_rows[{index}] missing runtime_action_id")
        if action_id in seen_actions:
            _issue(issues, f"duplicate reviewed runtime_action_id: {action_id}")
        seen_actions.add(action_id)
        if not row.get("runtime_action_receipt_id"):
            _issue(issues, f"review_rows[{index}] missing runtime_action_receipt_id")
        if not row.get("capability_id"):
            _issue(issues, f"review_rows[{index}] missing capability_id")
        if row.get("review_decision") not in {"ACCEPTED", "ACCEPTED_WITH_NOTES"}:
            _issue(issues, f"review_rows[{index}] must be accepted")
        else:
            accepted_rows += 1

    index_doc = pkg.get("source_adapter_runtime_acceptance_index")
    if not isinstance(index_doc, Mapping):
        _issue(issues, "source_adapter_runtime_acceptance_index is required")
        accepted_ids: set[str] = set()
    else:
        if index_doc.get("schema_version") != "source_adapter_runtime_acceptance_index_v1":
            _issue(issues, "acceptance index schema_version mismatch")
        if index_doc.get("acceptance_status") != "SOURCE_ADAPTER_RUNTIME_READY_FOR_UI_OR_PROVIDER_INTEGRATION":
            _issue(issues, "acceptance index status mismatch")
        accepted_ids = set(index_doc.get("runtime_action_ids") or [])
        if accepted_ids != seen_actions:
            _issue(issues, "acceptance index runtime_action_ids must match reviewed action ids")
        if index_doc.get("accepted_review_count") is not None and index_doc.get("accepted_review_count") != accepted_rows:
            _issue(issues, "accepted review count mismatch")

    handoff = pkg.get("source_adapter_runtime_acceptance_handoff")
    if not isinstance(handoff, Mapping):
        _issue(issues, "source_adapter_runtime_acceptance_handoff is required")
    else:
        if handoff.get("schema_version") != "source_adapter_runtime_acceptance_handoff_v1":
            _issue(issues, "runtime acceptance handoff schema_version mismatch")
        if handoff.get("handoff_status") != "SOURCE_ADAPTER_RUNTIME_READY_FOR_UI_OR_PROVIDER_INTEGRATION":
            _issue(issues, "runtime acceptance handoff status mismatch")
        if handoff.get("required_next_stage") != "source_adapter_runtime_ui_provider_integration":
            _issue(issues, "runtime acceptance handoff required_next_stage mismatch")
        if handoff.get("ready_for_runtime_ui_provider_integration") is not True:
            _issue(issues, "runtime acceptance handoff must be ready for integration")

    return {
        "schema_version": SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_runtime_receipt_review_bridge_id": bridge_id,
        "source_adapter_runtime_wiring_bridge_id": wiring_id,
        "runtime_receipt_review_count": len(rows),
        "accepted_review_count": accepted_rows,
        "handoff_status": str(handoff.get("handoff_status") if isinstance(handoff, Mapping) else ""),
    }
