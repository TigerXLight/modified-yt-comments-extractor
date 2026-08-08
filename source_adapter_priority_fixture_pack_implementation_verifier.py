from __future__ import annotations

from typing import Any, Mapping

from source_adapter_priority_fixture_pack_implementation import HANDOFF_STATUS, SCHEMA_VERSION, STATUS

VERIFIER_SCHEMA_VERSION = "source_adapter_priority_fixture_pack_implementation_verifier_v1"


def _rows(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, Mapping)]


def _unique(values: list[str]) -> bool:
    return len(values) == len(set(values))


def verify_source_adapter_priority_fixture_pack_implementation(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if package.get("schema_version") != SCHEMA_VERSION:
        issues.append({"issue_id": "unexpected_schema", "severity": "error", "message": "priority fixture pack implementation schema was not recognised"})
    if package.get("priority_fixture_pack_implementation_status") != STATUS:
        issues.append({"issue_id": "unexpected_status", "severity": "error", "message": "priority fixture pack implementation status is not built"})
    catalog = package.get("source_adapter_priority_fixture_pack_catalog") or {}
    execution_matrix = package.get("source_adapter_priority_fixture_pack_execution_matrix") or {}
    dispatch_batch = package.get("source_adapter_priority_fixture_pack_dispatch_receipt_batch") or {}
    gui_checklist = package.get("source_adapter_priority_fixture_pack_gui_installation_checklist") or {}
    named_site_queue = package.get("source_adapter_priority_fixture_pack_named_site_smoke_queue") or {}
    handoff = package.get("source_adapter_priority_fixture_pack_implementation_handoff") or {}
    pack_rows = _rows(catalog.get("fixture_pack_rows"))
    execution_rows = _rows(execution_matrix.get("execution_rows"))
    receipt_rows = _rows(dispatch_batch.get("dispatch_receipt_rows"))
    gui_rows = _rows(gui_checklist.get("gui_installation_rows"))
    smoke_rows = _rows(named_site_queue.get("named_site_smoke_queue_rows"))
    if catalog.get("fixture_pack_catalog_status") != "SOURCE_ADAPTER_PRIORITY_FIXTURE_PACK_CATALOG_READY" or len(pack_rows) != 5:
        issues.append({"issue_id": "fixture_pack_catalog_not_ready", "severity": "error", "message": "priority fixture pack catalog is not ready"})
    if execution_matrix.get("fixture_pack_execution_matrix_status") != "SOURCE_ADAPTER_PRIORITY_FIXTURE_PACK_EXECUTION_MATRIX_READY" or not execution_rows:
        issues.append({"issue_id": "execution_matrix_not_ready", "severity": "error", "message": "priority fixture execution matrix is not ready"})
    if dispatch_batch.get("fixture_pack_dispatch_receipt_batch_status") != "SOURCE_ADAPTER_PRIORITY_FIXTURE_PACK_DISPATCH_RECEIPTS_ACCEPTED" or len(receipt_rows) != len(execution_rows):
        issues.append({"issue_id": "dispatch_receipts_not_accepted", "severity": "error", "message": "priority fixture pack dispatch receipts are not accepted"})
    if gui_checklist.get("gui_installation_checklist_status") != "SOURCE_ADAPTER_PRIORITY_FIXTURE_PACK_GUI_INSTALLATION_READY" or not gui_rows:
        issues.append({"issue_id": "gui_installation_not_ready", "severity": "error", "message": "fixture pack GUI installation checklist is not ready"})
    if named_site_queue.get("named_site_smoke_queue_status") != "SOURCE_ADAPTER_PRIORITY_FIXTURE_PACK_NAMED_SITE_SMOKE_QUEUE_READY" or len(smoke_rows) != len(pack_rows):
        issues.append({"issue_id": "named_site_smoke_queue_not_ready", "severity": "error", "message": "named-site smoke queue is not ready"})
    if handoff.get("handoff_status") != HANDOFF_STATUS:
        issues.append({"issue_id": "handoff_not_ready", "severity": "error", "message": "priority fixture pack implementation handoff is not ready"})
    if package.get("operator_summary", {}).get("keys_accounts_label") != "KEYS/ACCOUNTS":
        issues.append({"issue_id": "keys_accounts_label_changed", "severity": "error", "message": "KEYS/ACCOUNTS label was not preserved"})
    if not _unique([str(row.get("fixture_pack_id")) for row in pack_rows]):
        issues.append({"issue_id": "duplicate_fixture_pack_ids", "severity": "error", "message": "fixture pack ids are not unique"})
    for row in receipt_rows:
        if row.get("missing_receipt_fields"):
            issues.append({"issue_id": "missing_receipt_fields", "severity": "error", "message": str(row.get("runtime_dispatch_receipt_id"))})
        if row.get("dispatch_acceptance_status") != "ACCEPTED_FOR_PRIORITY_FIXTURE_PACK_REGRESSION":
            issues.append({"issue_id": "dispatch_receipt_not_accepted", "severity": "error", "message": str(row.get("runtime_dispatch_receipt_id"))})
    verified = not issues
    return {
        "schema_version": VERIFIER_SCHEMA_VERSION,
        "verified": verified,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_priority_fixture_pack_implementation_id": package.get("source_adapter_priority_fixture_pack_implementation_id"),
        "fixture_pack_count": len(pack_rows),
        "fixture_pack_execution_row_count": len(execution_rows),
        "dispatch_receipt_count": len(receipt_rows),
        "gui_installation_row_count": len(gui_rows),
        "named_site_smoke_queue_count": len(smoke_rows),
        "handoff_status": handoff.get("handoff_status"),
    }
