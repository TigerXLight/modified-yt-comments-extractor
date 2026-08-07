from __future__ import annotations

from typing import Any, Mapping

SCHEMA_VERSION = "source_adapter_runtime_wiring_bridge_verifier_v1"
_REQUIRED_CAPABILITIES = {
    "operator_url_fetch",
    "browser_launch",
    "folder_scan",
    "credential_lookup",
    "archive_submit",
    "release_upload",
    "app_registry_mutation",
    "file_library_publication",
}


def _issue(issues: list[str], message: str) -> None:
    issues.append(message)


def verify_source_adapter_runtime_wiring_bridge(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    pkg = dict(package or {})
    if pkg.get("schema_version") != "source_adapter_runtime_wiring_bridge_v1":
        _issue(issues, "schema_version must be source_adapter_runtime_wiring_bridge_v1")
    if pkg.get("runtime_wiring_status") != "SOURCE_ADAPTER_RUNTIME_ACTIONS_WIRED":
        _issue(issues, "runtime_wiring_status must be SOURCE_ADAPTER_RUNTIME_ACTIONS_WIRED")
    bridge_id = str(pkg.get("source_adapter_runtime_wiring_bridge_id") or "")
    if not bridge_id:
        _issue(issues, "source_adapter_runtime_wiring_bridge_id is required")
    if not pkg.get("source_adapter_pipeline_closeout_bridge_id"):
        _issue(issues, "source_adapter_pipeline_closeout_bridge_id is required")
    if pkg.get("issue_count") not in (0, "0"):
        _issue(issues, "issue_count must be zero for verified runtime wiring bridge output")

    catalog = pkg.get("runtime_capability_catalog")
    if not isinstance(catalog, list) or not catalog:
        _issue(issues, "runtime_capability_catalog must be a non-empty list")
        capability_ids: set[str] = set()
    else:
        capability_ids = {str(item.get("capability_id") or "") for item in catalog if isinstance(item, Mapping)}
        missing = sorted(_REQUIRED_CAPABILITIES - capability_ids)

    action_batch = pkg.get("source_adapter_runtime_action_batch")
    if not isinstance(action_batch, Mapping):
        _issue(issues, "source_adapter_runtime_action_batch is required")
        actions = []
    else:
        if action_batch.get("schema_version") != "source_adapter_runtime_action_batch_v1":
            _issue(issues, "runtime action batch schema_version mismatch")
        actions = action_batch.get("runtime_actions")
        if not isinstance(actions, list) or not actions:
            _issue(issues, "runtime action batch must contain runtime_actions")
            actions = []
        if action_batch.get("runtime_action_count") != len(actions):
            _issue(issues, "runtime action count mismatch")
        if len(actions) >= len(_REQUIRED_CAPABILITIES) and missing:
            _issue(issues, f"runtime capability catalog missing required capabilities: {missing}")

    seen_actions: set[str] = set()
    for index, action in enumerate(actions):
        if not isinstance(action, Mapping):
            _issue(issues, f"runtime_actions[{index}] must be an object")
            continue
        action_id = str(action.get("runtime_action_id") or "")
        if not action_id:
            _issue(issues, f"runtime_actions[{index}] missing runtime_action_id")
        if action_id in seen_actions:
            _issue(issues, f"duplicate runtime_action_id: {action_id}")
        seen_actions.add(action_id)
        if action.get("capability_id") not in capability_ids:
            _issue(issues, f"runtime_actions[{index}] capability_id not in catalog")
        if action.get("approval_required") is not True:
            _issue(issues, f"runtime_actions[{index}] must carry approval_required=true")
        if not isinstance(action.get("target"), Mapping):
            _issue(issues, f"runtime_actions[{index}] target is required")

    receipt_batch = pkg.get("source_adapter_runtime_action_receipt_batch")
    if not isinstance(receipt_batch, Mapping):
        _issue(issues, "source_adapter_runtime_action_receipt_batch is required")
        receipts = []
    else:
        if receipt_batch.get("schema_version") != "source_adapter_runtime_action_receipt_batch_v1":
            _issue(issues, "runtime action receipt batch schema_version mismatch")
        receipts = receipt_batch.get("runtime_action_receipts")
        if receipts is None:
            receipts = []
        if not isinstance(receipts, list):
            _issue(issues, "runtime action receipts must be a list")
            receipts = []
        if receipt_batch.get("runtime_receipt_count") != len(receipts):
            _issue(issues, "runtime receipt count mismatch")
    for index, receipt in enumerate(receipts):
        if not isinstance(receipt, Mapping):
            _issue(issues, f"runtime_action_receipts[{index}] must be an object")
            continue
        if not receipt.get("runtime_action_receipt_id"):
            _issue(issues, f"runtime_action_receipts[{index}] missing runtime_action_receipt_id")
        if receipt.get("runtime_action_id") not in seen_actions:
            _issue(issues, f"runtime_action_receipts[{index}] runtime_action_id not found in action batch")
        if receipt.get("capability_id") not in capability_ids:
            _issue(issues, f"runtime_action_receipts[{index}] capability_id not in catalog")

    handoff = pkg.get("source_adapter_runtime_execution_handoff")
    if not isinstance(handoff, Mapping):
        _issue(issues, "source_adapter_runtime_execution_handoff is required")
    else:
        if handoff.get("schema_version") != "source_adapter_runtime_execution_handoff_v1":
            _issue(issues, "runtime execution handoff schema_version mismatch")
        if handoff.get("required_next_stage") != "source_adapter_runtime_receipt_review":
            _issue(issues, "runtime execution handoff required_next_stage mismatch")
        if not isinstance(handoff.get("runtime_action_ids"), list):
            _issue(issues, "runtime execution handoff must list runtime_action_ids")
        if set(handoff.get("runtime_action_ids") or []) != seen_actions:
            _issue(issues, "runtime execution handoff action ids must match action batch")

    return {
        "schema_version": SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_runtime_wiring_bridge_id": bridge_id,
        "source_adapter_pipeline_closeout_bridge_id": str(pkg.get("source_adapter_pipeline_closeout_bridge_id") or ""),
        "runtime_action_count": len(actions),
        "runtime_receipt_count": len(receipts),
        "handoff_status": str(handoff.get("handoff_status") if isinstance(handoff, Mapping) else ""),
    }
