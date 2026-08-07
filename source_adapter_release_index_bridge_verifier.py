from __future__ import annotations

from typing import Any, Mapping

from source_release_index_verifier import verify_source_release_index

SCHEMA_VERSION = "source_adapter_release_index_bridge_verifier_v1"


def _issue(issues: list[str], message: str) -> None:
    issues.append(message)


def verify_source_adapter_release_index_bridge(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    pkg = dict(package or {})
    if pkg.get("schema_version") != "source_adapter_release_index_bridge_v1":
        _issue(issues, "schema_version must be source_adapter_release_index_bridge_v1")
    if pkg.get("release_index_bridge_status") != "SHARED_RELEASE_INDEXES_BUILT":
        _issue(issues, "release_index_bridge_status must be SHARED_RELEASE_INDEXES_BUILT")
    if not pkg.get("source_adapter_release_index_bridge_id"):
        _issue(issues, "source_adapter_release_index_bridge_id is required")
    if pkg.get("issue_count") not in (0, "0"):
        _issue(issues, "issue_count must be zero for verified release index bridge output")

    outputs = pkg.get("release_index_outputs")
    if not isinstance(outputs, list) or not outputs:
        _issue(issues, "release_index_outputs must be a non-empty list")
    else:
        seen: set[str] = set()
        for index, output in enumerate(outputs):
            if not isinstance(output, Mapping):
                _issue(issues, f"release_index_outputs[{index}] must be an object")
                continue
            record = output.get("release_index_record")
            inventory = output.get("release_inventory")
            handoff = output.get("export_bundle_handoff")
            if not isinstance(record, Mapping):
                _issue(issues, f"release_index_outputs[{index}] missing release_index_record")
                continue
            release_index_id = str(record.get("release_index_id") or "")
            if release_index_id in seen:
                _issue(issues, f"duplicate release_index_id: {release_index_id}")
            seen.add(release_index_id)
            verification = verify_source_release_index(
                record,
                inventory if isinstance(inventory, Mapping) else None,
                handoff if isinstance(handoff, Mapping) else None,
            )
            if not verification.get("verified"):
                _issue(issues, f"release_index_outputs[{index}] failed shared verification: {verification.get('issues')}")

    batch = pkg.get("source_adapter_release_index_batch")
    if not isinstance(batch, Mapping):
        _issue(issues, "source_adapter_release_index_batch is required")
    else:
        if batch.get("schema_version") != "source_adapter_release_index_batch_v1":
            _issue(issues, "source_adapter_release_index_batch schema_version mismatch")
        if batch.get("release_index_count") != len(outputs or []):
            _issue(issues, "source_adapter_release_index_batch release_index_count mismatch")
        if not isinstance(batch.get("release_index_rows"), list) or not batch.get("release_index_rows"):
            _issue(issues, "source_adapter_release_index_batch must include release_index_rows")

    handoff = pkg.get("source_adapter_release_audit_batch_handoff")
    if not isinstance(handoff, Mapping):
        _issue(issues, "source_adapter_release_audit_batch_handoff is required")
    else:
        if handoff.get("schema_version") != "source_adapter_release_audit_batch_handoff_v1":
            _issue(issues, "source_adapter_release_audit_batch_handoff schema_version mismatch")
        if handoff.get("handoff_status") != "READY_FOR_SHARED_RELEASE_AUDIT":
            _issue(issues, "release audit handoff must be READY_FOR_SHARED_RELEASE_AUDIT")
        if handoff.get("ready_for_release_audit") is not True:
            _issue(issues, "release audit handoff must be ready_for_release_audit")
        if handoff.get("required_next_stage") != "source_release_audit":
            _issue(issues, "release audit handoff required_next_stage must be source_release_audit")

    return {
        "schema_version": SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_release_index_bridge_id": str(pkg.get("source_adapter_release_index_bridge_id") or ""),
        "source_adapter_approved_release_bridge_id": str(pkg.get("source_adapter_approved_release_bridge_id") or ""),
        "release_index_count": len(outputs) if isinstance(outputs, list) else 0,
        "handoff_status": str(handoff.get("handoff_status") if isinstance(handoff, Mapping) else ""),
    }
