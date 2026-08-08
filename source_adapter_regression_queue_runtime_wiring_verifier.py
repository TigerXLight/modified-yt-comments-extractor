from __future__ import annotations

from typing import Any, Mapping

from source_adapter_regression_queue_runtime_wiring import (
    ACCEPTANCE_RECEIPT_BATCH_STATUS,
    DRY_RUN_MODE,
    EXPANDED_BINDING_STATUS,
    GUI_CALL_SITE_WIRING_STATUS,
    HANDOFF_STATUS,
    KEYS_ACCOUNTS_LABEL,
    LOCAL_RUNNER_QUEUE_STATUS,
    SCHEMA_VERSION,
    SMOKE_GATE_CARRY_FORWARD_STATUS,
    STATUS,
)

VERIFIER_SCHEMA_VERSION = "source_adapter_regression_queue_runtime_wiring_verifier_v1"
FORBIDDEN_SECRET_KEYS = {
    "api_key",
    "secret",
    "token",
    "password",
    "cookie",
    "authorization",
    "credential_value",
    "raw_credential",
}
FORBIDDEN_VALUE_MARKERS = ("sk-", "Bearer ", "BEGIN PRIVATE KEY", "sessionid=", "password=")


def _rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(row) for row in value if isinstance(row, Mapping)]


def _walk_secret_like(value: Any, path: str = "package") -> list[str]:
    findings: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            key_normalized = key_text.lower().replace("-", "_")
            if key_normalized in FORBIDDEN_SECRET_KEYS:
                findings.append(f"{path}.{key_text}")
            findings.extend(_walk_secret_like(item, f"{path}.{key_text}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(_walk_secret_like(item, f"{path}[{index}]"))
    elif isinstance(value, str):
        if any(marker in value for marker in FORBIDDEN_VALUE_MARKERS):
            findings.append(path)
    return findings


def verify_source_adapter_regression_queue_runtime_wiring(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if package.get("schema_version") != SCHEMA_VERSION:
        issues.append({"issue_id": "unexpected_schema", "severity": "error", "message": "regression queue runtime wiring schema was not recognised"})
    if package.get("regression_queue_runtime_wiring_status") != STATUS:
        issues.append({"issue_id": "unexpected_status", "severity": "error", "message": "regression queue runtime wiring is not built"})

    local_runner_queue = package.get("source_adapter_local_regression_runner_queue_installation") or {}
    expanded_binding_matrix = package.get("source_adapter_runtime_controller_provider_expanded_binding_matrix") or {}
    gui_wiring = package.get("source_adapter_gui_controller_call_site_runtime_wiring") or {}
    acceptance_receipts = package.get("source_adapter_local_regression_acceptance_receipt_batch") or {}
    smoke_gate = package.get("source_adapter_named_site_smoke_gate_carry_forward") or {}
    handoff = package.get("source_adapter_regression_queue_runtime_wiring_handoff") or {}
    summary = package.get("operator_summary") or {}

    local_rows = _rows(local_runner_queue.get("local_runner_queue_rows")) if isinstance(local_runner_queue, Mapping) else []
    binding_rows = _rows(expanded_binding_matrix.get("expanded_binding_rows")) if isinstance(expanded_binding_matrix, Mapping) else []
    gui_rows = _rows(gui_wiring.get("gui_call_site_wiring_rows")) if isinstance(gui_wiring, Mapping) else []
    receipt_rows = _rows(acceptance_receipts.get("local_regression_acceptance_receipt_rows")) if isinstance(acceptance_receipts, Mapping) else []
    smoke_rows = _rows(smoke_gate.get("smoke_gate_carry_forward_rows")) if isinstance(smoke_gate, Mapping) else []

    if local_runner_queue.get("local_runner_queue_status") != LOCAL_RUNNER_QUEUE_STATUS or len(local_rows) != 20:
        issues.append({"issue_id": "local_runner_queue_not_installed", "severity": "error", "message": "expected twenty local runner queue rows"})
    if expanded_binding_matrix.get("expanded_binding_matrix_status") != EXPANDED_BINDING_STATUS or len(binding_rows) != 20:
        issues.append({"issue_id": "expanded_binding_matrix_not_ready", "severity": "error", "message": "expected twenty expanded binding rows"})
    if gui_wiring.get("gui_call_site_runtime_wiring_status") != GUI_CALL_SITE_WIRING_STATUS or len(gui_rows) < 4:
        issues.append({"issue_id": "gui_call_site_wiring_not_ready", "severity": "error", "message": "expected GUI/controller call-site wiring rows"})
    if acceptance_receipts.get("acceptance_receipt_batch_status") != ACCEPTANCE_RECEIPT_BATCH_STATUS or len(receipt_rows) != 20:
        issues.append({"issue_id": "acceptance_receipts_not_ready", "severity": "error", "message": "expected twenty local regression acceptance receipts"})
    if smoke_gate.get("smoke_gate_carry_forward_status") != SMOKE_GATE_CARRY_FORWARD_STATUS or len(smoke_rows) != 5:
        issues.append({"issue_id": "smoke_gate_not_carried_forward", "severity": "error", "message": "expected five unexecuted named-site smoke gate rows"})
    if handoff.get("handoff_status") != HANDOFF_STATUS:
        issues.append({"issue_id": "handoff_not_ready", "severity": "error", "message": "runtime wiring handoff is not ready"})
    if summary.get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
        issues.append({"issue_id": "keys_accounts_label_changed", "severity": "error", "message": "KEYS/ACCOUNTS label was not preserved"})

    for row in local_rows:
        row_id = str(row.get("local_runner_queue_row_id") or row.get("row_index"))
        if row.get("execution_mode") != DRY_RUN_MODE:
            issues.append({"issue_id": "local_runner_row_not_dry_run", "severity": "error", "message": row_id})
        for field in ("execution_performed", "provider_call_performed", "controller_call_performed", "live_execution_allowed", "network_allowed", "archive_submission_performed", "release_upload_performed", "file_library_mutation_performed", "credential_storage_allowed"):
            if row.get(field) is not False:
                issues.append({"issue_id": f"local_runner_{field}_not_false", "severity": "error", "message": row_id})
        if row.get("queue_installation_status") != "INSTALLED_FOR_LOCAL_REGRESSION_DRY_RUN":
            issues.append({"issue_id": "local_runner_row_not_installed", "severity": "error", "message": row_id})
        if row.get("missing_receipt_fields"):
            issues.append({"issue_id": "local_runner_missing_receipt_fields", "severity": "error", "message": row_id})
        if row.get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
            issues.append({"issue_id": "local_runner_keys_accounts_label_changed", "severity": "error", "message": row_id})

    for row in binding_rows:
        row_id = str(row.get("expanded_binding_row_id") or row.get("row_index"))
        if row.get("binding_status") != "BOUND_FOR_LOCAL_REGRESSION_DRY_RUN":
            issues.append({"issue_id": "expanded_binding_not_bound", "severity": "error", "message": row_id})
        for field in ("provider_call_allowed", "network_allowed", "credential_storage_allowed"):
            if row.get(field) is not False:
                issues.append({"issue_id": f"expanded_binding_{field}_not_false", "severity": "error", "message": row_id})
        if row.get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
            issues.append({"issue_id": "expanded_binding_keys_accounts_label_changed", "severity": "error", "message": row_id})

    for row in gui_rows:
        row_id = str(row.get("gui_call_site_runtime_wiring_row_id") or row.get("row_index"))
        if row.get("wiring_status") != "WIRED_IN_LOCAL_RUNTIME_REGISTRY_FOR_DRY_RUN":
            issues.append({"issue_id": "gui_call_site_not_wired", "severity": "error", "message": row_id})
        for field in ("gui_mutation_performed", "runtime_route_mutation_performed", "controller_call_performed", "provider_call_performed", "network_allowed", "credential_storage_allowed"):
            if row.get(field) is not False:
                issues.append({"issue_id": f"gui_wiring_{field}_not_false", "severity": "error", "message": row_id})
        if row.get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
            issues.append({"issue_id": "gui_wiring_keys_accounts_label_changed", "severity": "error", "message": row_id})

    for row in receipt_rows:
        row_id = str(row.get("local_regression_acceptance_receipt_id") or row.get("row_index"))
        if row.get("execution_mode") != DRY_RUN_MODE:
            issues.append({"issue_id": "acceptance_receipt_not_dry_run", "severity": "error", "message": row_id})
        if row.get("accepted_for_closeout_audit") is not True:
            issues.append({"issue_id": "acceptance_receipt_not_accepted", "severity": "error", "message": row_id})
        for field in ("provider_call_performed", "controller_call_performed", "live_execution_allowed", "network_allowed", "archive_submission_performed", "release_upload_performed", "file_library_mutation_performed", "credential_storage_allowed", "credential_secret_material_present"):
            if row.get(field) is not False:
                issues.append({"issue_id": f"acceptance_receipt_{field}_not_false", "severity": "error", "message": row_id})
        if row.get("missing_receipt_fields"):
            issues.append({"issue_id": "acceptance_receipt_missing_fields", "severity": "error", "message": row_id})
        if row.get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
            issues.append({"issue_id": "acceptance_receipt_keys_accounts_label_changed", "severity": "error", "message": row_id})

    for row in smoke_rows:
        row_id = str(row.get("smoke_gate_carry_forward_row_id") or row.get("row_index"))
        if row.get("operator_approval_required") is not True:
            issues.append({"issue_id": "smoke_gate_without_operator_approval", "severity": "error", "message": row_id})
        for field in ("operator_approved", "execution_performed", "smoke_executed", "live_execution_allowed", "network_allowed", "provider_call_performed", "credential_storage_allowed"):
            if row.get(field) is not False:
                issues.append({"issue_id": f"smoke_gate_{field}_not_false", "severity": "error", "message": row_id})
        if row.get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
            issues.append({"issue_id": "smoke_gate_keys_accounts_label_changed", "severity": "error", "message": row_id})
        if row.get("redacted_credential_reference_required") is not True:
            issues.append({"issue_id": "smoke_gate_redacted_reference_not_required", "severity": "error", "message": row_id})

    secret_findings = _walk_secret_like(package)
    if secret_findings:
        issues.append({"issue_id": "secret_like_material_present", "severity": "error", "message": "; ".join(secret_findings[:5])})

    verified = not issues
    return {
        "schema_version": VERIFIER_SCHEMA_VERSION,
        "verified": verified,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_regression_queue_runtime_wiring_id": package.get("source_adapter_regression_queue_runtime_wiring_id"),
        "local_runner_queue_row_count": len(local_rows),
        "expanded_binding_row_count": len(binding_rows),
        "call_site_wiring_row_count": len(gui_rows),
        "acceptance_receipt_row_count": len(receipt_rows),
        "named_site_smoke_gate_row_count": len(smoke_rows),
        "handoff_status": handoff.get("handoff_status") if isinstance(handoff, Mapping) else None,
    }
