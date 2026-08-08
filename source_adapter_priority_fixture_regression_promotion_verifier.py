from __future__ import annotations

from typing import Any, Mapping

from source_adapter_priority_fixture_regression_promotion import (
    DRY_RUN_MODE,
    GUI_CALL_SITE_PLAN_STATUS,
    HANDOFF_STATUS,
    KEYS_ACCOUNTS_LABEL,
    NAMED_SITE_SMOKE_GATE_STATUS,
    REGRESSION_QUEUE_STATUS,
    SCHEMA_VERSION,
    STATUS,
)

VERIFIER_SCHEMA_VERSION = "source_adapter_priority_fixture_regression_promotion_verifier_v1"
FORBIDDEN_SECRET_KEYS = {
    "api_key",
    "access_token",
    "refresh_token",
    "password",
    "cookie",
    "authorization",
    "client_secret",
    "secret_key",
}
FORBIDDEN_VALUE_MARKERS = ("sk-", "ghp_", "xoxb-", "BEGIN PRIVATE KEY", "Bearer ")


def _rows(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, Mapping)]


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


def verify_source_adapter_priority_fixture_regression_promotion(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if package.get("schema_version") != SCHEMA_VERSION:
        issues.append({"issue_id": "unexpected_schema", "severity": "error", "message": "priority fixture regression promotion schema was not recognised"})
    if package.get("priority_fixture_regression_promotion_status") != STATUS:
        issues.append({"issue_id": "unexpected_status", "severity": "error", "message": "priority fixture regression promotion is not built"})
    regression_queue = package.get("source_adapter_priority_fixture_regression_queue") or {}
    gui_plan = package.get("source_adapter_gui_controller_call_site_installation_plan") or {}
    smoke_gate = package.get("source_adapter_named_site_smoke_operator_approval_gate") or {}
    handoff = package.get("source_adapter_priority_fixture_regression_promotion_handoff") or {}
    summary = package.get("operator_summary") or {}

    queue_rows = _rows(regression_queue.get("promoted_regression_queue_rows")) if isinstance(regression_queue, Mapping) else []
    gui_rows = _rows(gui_plan.get("call_site_installation_rows")) if isinstance(gui_plan, Mapping) else []
    smoke_rows = _rows(smoke_gate.get("named_site_smoke_gate_rows")) if isinstance(smoke_gate, Mapping) else []

    if regression_queue.get("regression_queue_status") != REGRESSION_QUEUE_STATUS or len(queue_rows) != 20:
        issues.append({"issue_id": "regression_queue_not_ready", "severity": "error", "message": "expected twenty promoted regression queue rows"})
    if int(regression_queue.get("fixture_pack_count", 0) or 0) != 5:
        issues.append({"issue_id": "fixture_pack_count_mismatch", "severity": "error", "message": "expected five fixture pack families"})
    if gui_plan.get("gui_controller_call_site_installation_plan_status") != GUI_CALL_SITE_PLAN_STATUS or len(gui_rows) < 4:
        issues.append({"issue_id": "gui_call_site_plan_not_ready", "severity": "error", "message": "GUI/controller call-site installation plan is not ready"})
    if smoke_gate.get("named_site_smoke_approval_gate_status") != NAMED_SITE_SMOKE_GATE_STATUS or len(smoke_rows) != 5:
        issues.append({"issue_id": "named_site_smoke_gate_not_ready", "severity": "error", "message": "named-site smoke approval gate is not ready"})
    if handoff.get("handoff_status") != HANDOFF_STATUS:
        issues.append({"issue_id": "handoff_not_ready", "severity": "error", "message": "priority fixture regression promotion handoff is not ready"})
    if summary.get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
        issues.append({"issue_id": "keys_accounts_label_changed", "severity": "error", "message": "KEYS/ACCOUNTS label was not preserved"})

    for row in queue_rows:
        row_id = str(row.get("promoted_regression_queue_row_id") or row.get("row_index"))
        if row.get("execution_mode") != DRY_RUN_MODE:
            issues.append({"issue_id": "promoted_row_not_dry_run", "severity": "error", "message": row_id})
        for field in ("live_execution_allowed", "network_allowed", "provider_call_allowed", "archive_submission_allowed", "release_upload_allowed", "file_library_mutation_allowed", "credential_storage_allowed"):
            if row.get(field) is not False:
                issues.append({"issue_id": f"promoted_row_{field}_not_false", "severity": "error", "message": row_id})
        if row.get("execution_performed") is not False:
            issues.append({"issue_id": "promoted_row_claims_execution", "severity": "error", "message": row_id})
        if row.get("missing_receipt_fields"):
            issues.append({"issue_id": "missing_receipt_fields", "severity": "error", "message": row_id})
        if row.get("source_dispatch_acceptance_status") != "ACCEPTED_FOR_PRIORITY_FIXTURE_PACK_REGRESSION":
            issues.append({"issue_id": "source_dispatch_not_accepted", "severity": "error", "message": row_id})
        if row.get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
            issues.append({"issue_id": "row_keys_accounts_label_changed", "severity": "error", "message": row_id})

    for row in gui_rows:
        row_id = str(row.get("call_site_installation_row_id") or row.get("row_index"))
        if row.get("installation_mode") != "local_plan_only":
            issues.append({"issue_id": "gui_plan_not_local_only", "severity": "error", "message": row_id})
        for field in ("gui_mutation_performed", "runtime_route_mutation_performed", "controller_call_performed", "network_allowed", "credential_storage_allowed"):
            if row.get(field) is not False:
                issues.append({"issue_id": f"gui_plan_{field}_not_false", "severity": "error", "message": row_id})
        if row.get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
            issues.append({"issue_id": "gui_plan_keys_accounts_label_changed", "severity": "error", "message": row_id})

    for row in smoke_rows:
        row_id = str(row.get("named_site_smoke_gate_row_id") or row.get("row_index"))
        if row.get("operator_approval_required") is not True:
            issues.append({"issue_id": "smoke_gate_without_operator_approval", "severity": "error", "message": row_id})
        for field in ("operator_approved", "execution_performed", "smoke_executed", "live_execution_allowed", "credential_storage_allowed"):
            if row.get(field) is not False:
                issues.append({"issue_id": f"smoke_gate_{field}_not_false", "severity": "error", "message": row_id})
        if row.get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
            issues.append({"issue_id": "smoke_gate_keys_accounts_label_changed", "severity": "error", "message": row_id})
        required = set(row.get("receipt_capture_requirements") or [])
        if "redacted_credential_reference_hash" not in required:
            issues.append({"issue_id": "smoke_gate_redacted_hash_not_required", "severity": "error", "message": row_id})

    secret_findings = _walk_secret_like(package)
    if secret_findings:
        issues.append({"issue_id": "secret_like_material_present", "severity": "error", "message": "; ".join(secret_findings[:5])})

    verified = not issues
    return {
        "schema_version": VERIFIER_SCHEMA_VERSION,
        "verified": verified,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_priority_fixture_regression_promotion_id": package.get("source_adapter_priority_fixture_regression_promotion_id"),
        "fixture_pack_count": regression_queue.get("fixture_pack_count", 0) if isinstance(regression_queue, Mapping) else 0,
        "promoted_regression_queue_row_count": len(queue_rows),
        "call_site_installation_row_count": len(gui_rows),
        "named_site_smoke_gate_row_count": len(smoke_rows),
        "handoff_status": handoff.get("handoff_status") if isinstance(handoff, Mapping) else None,
    }
