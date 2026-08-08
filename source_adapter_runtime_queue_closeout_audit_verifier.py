from __future__ import annotations

from typing import Any, Mapping, Sequence

from source_adapter_runtime_queue_closeout_audit import (
    COVERAGE_MATRIX_STATUS,
    KEYS_ACCOUNTS_LABEL,
    OPERATOR_HANDOFF_STATUS,
    RELEASE_GATE_STATUS,
    ROADMAP_STATE_STATUS,
    SCHEMA_VERSION,
    STATUS,
)

VERIFIER_SCHEMA_VERSION = "source_adapter_runtime_queue_closeout_audit_verifier_v1"
FORBIDDEN_KEY_MARKERS = ("secret", "token", "password", "cookie", "api_key_value", "credential_value")
FORBIDDEN_VALUE_MARKERS = ("BEGIN PRIVATE KEY", "sk-", "xoxb-", "AIza")


def _rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [dict(row) for row in value if isinstance(row, Mapping)]


def _walk_secret_like(value: Any, path: str = "package") -> list[str]:
    findings: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key).lower()
            child_path = f"{path}.{key}"
            if any(marker in key_text for marker in FORBIDDEN_KEY_MARKERS):
                if key_text not in {"credential_storage_allowed", "credential_references_preserved_redacted", "redacted_credential_reference_required", "credential_storage"}:
                    findings.append(child_path)
            findings.extend(_walk_secret_like(item, child_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(_walk_secret_like(item, f"{path}[{index}]"))
    elif isinstance(value, str):
        if any(marker in value for marker in FORBIDDEN_VALUE_MARKERS):
            findings.append(path)
    return findings


def verify_source_adapter_runtime_queue_closeout_audit(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if package.get("schema_version") != SCHEMA_VERSION:
        issues.append({"issue_id": "unexpected_schema", "severity": "error", "message": "runtime queue closeout audit schema was not recognised"})
    if package.get("runtime_queue_closeout_audit_status") != STATUS:
        issues.append({"issue_id": "unexpected_status", "severity": "error", "message": "runtime queue closeout audit is not built"})

    coverage = package.get("source_adapter_runtime_queue_closeout_coverage_matrix") or {}
    roadmap = package.get("source_adapter_runtime_queue_closeout_roadmap_state") or {}
    release_gate = package.get("source_adapter_runtime_queue_closeout_release_gate") or {}
    handoff = package.get("source_adapter_runtime_queue_closeout_operator_handoff") or {}
    summary = package.get("operator_summary") or {}

    coverage_rows = _rows(coverage.get("coverage_rows")) if isinstance(coverage, Mapping) else []
    if coverage.get("coverage_matrix_status") != COVERAGE_MATRIX_STATUS:
        issues.append({"issue_id": "coverage_matrix_not_ready", "severity": "error", "message": "coverage matrix status is not ready"})
    if coverage.get("local_runner_queue_row_count") != 20:
        issues.append({"issue_id": "local_runner_queue_count_mismatch", "severity": "error", "message": "expected twenty local runner queue rows"})
    if coverage.get("expanded_binding_row_count") != 20:
        issues.append({"issue_id": "expanded_binding_count_mismatch", "severity": "error", "message": "expected twenty expanded binding rows"})
    if coverage.get("acceptance_receipt_row_count") != 20:
        issues.append({"issue_id": "acceptance_receipt_count_mismatch", "severity": "error", "message": "expected twenty acceptance receipts"})
    if coverage.get("named_site_smoke_gate_row_count") != 5:
        issues.append({"issue_id": "smoke_gate_count_mismatch", "severity": "error", "message": "expected five named-site smoke gate rows"})
    if len(coverage_rows) < 6:
        issues.append({"issue_id": "coverage_rows_missing", "severity": "error", "message": "expected closeout coverage rows"})
    for row in coverage_rows:
        row_id = str(row.get("coverage_row_id") or row.get("coverage_area"))
        if row.get("coverage_ready") is not True:
            issues.append({"issue_id": "coverage_row_not_ready", "severity": "error", "message": row_id})
        for field in ("live_execution_allowed", "network_allowed", "credential_storage_allowed"):
            if row.get(field) is not False:
                issues.append({"issue_id": f"coverage_row_{field}_not_false", "severity": "error", "message": row_id})
        if row.get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
            issues.append({"issue_id": "coverage_row_keys_accounts_label_changed", "severity": "error", "message": row_id})

    if roadmap.get("roadmap_state_status") != ROADMAP_STATE_STATUS:
        issues.append({"issue_id": "roadmap_state_not_updated", "severity": "error", "message": "roadmap state status is not updated"})
    roadmap_projection = roadmap.get("roadmap_projection") or {}
    if not isinstance(roadmap_projection, Mapping) or not all(roadmap_projection.get(key) is True for key in (
        "local_regression_runner_queue_installed",
        "expanded_controller_provider_bindings_ready",
        "gui_controller_call_site_wiring_ready",
        "local_acceptance_receipts_ready",
        "named_site_smoke_still_operator_approval_gated",
        "runtime_closeout_audit_recorded",
    )):
        issues.append({"issue_id": "roadmap_projection_incomplete", "severity": "error", "message": "roadmap projection is incomplete"})
    if roadmap.get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
        issues.append({"issue_id": "roadmap_keys_accounts_label_changed", "severity": "error", "message": "roadmap state changed the KEYS/ACCOUNTS label"})

    if release_gate.get("release_gate_status") != RELEASE_GATE_STATUS:
        issues.append({"issue_id": "release_gate_not_ready", "severity": "error", "message": "release gate status is not ready"})
    if release_gate.get("ready_for_operator_named_site_selection") is not True:
        issues.append({"issue_id": "operator_named_site_selection_not_ready", "severity": "error", "message": "operator named-site selection should be ready"})
    for field in (
        "ready_for_live_smoke_execution",
        "ready_for_browser_automation",
        "ready_for_network_or_provider_calls",
        "ready_for_archive_submission",
        "ready_for_release_upload",
        "ready_for_file_library_mutation",
        "ready_for_credential_storage",
    ):
        if release_gate.get(field) is not False:
            issues.append({"issue_id": f"release_gate_{field}_not_false", "severity": "error", "message": field})
    for field in ("requires_explicit_operator_approval_before_smoke", "requires_named_site_inputs_before_smoke", "requires_receipt_review_after_smoke"):
        if release_gate.get(field) is not True:
            issues.append({"issue_id": f"release_gate_{field}_not_true", "severity": "error", "message": field})

    if handoff.get("handoff_status") != OPERATOR_HANDOFF_STATUS:
        issues.append({"issue_id": "operator_handoff_not_ready", "severity": "error", "message": "operator handoff is not ready"})
    if handoff.get("named_site_smoke_still_approval_gated") is not True:
        issues.append({"issue_id": "handoff_smoke_gate_not_preserved", "severity": "error", "message": "named-site smoke gate was not preserved"})
    if summary.get("keys_accounts_label") != KEYS_ACCOUNTS_LABEL:
        issues.append({"issue_id": "summary_keys_accounts_label_changed", "severity": "error", "message": "summary changed the KEYS/ACCOUNTS label"})

    secret_findings = _walk_secret_like(package)
    if secret_findings:
        issues.append({"issue_id": "secret_like_material_present", "severity": "error", "message": "; ".join(secret_findings[:5])})

    verified = not issues
    return {
        "schema_version": VERIFIER_SCHEMA_VERSION,
        "verified": verified,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_runtime_queue_closeout_audit_id": package.get("source_adapter_runtime_queue_closeout_audit_id"),
        "coverage_row_count": len(coverage_rows),
        "local_runner_queue_row_count": coverage.get("local_runner_queue_row_count") if isinstance(coverage, Mapping) else None,
        "expanded_binding_row_count": coverage.get("expanded_binding_row_count") if isinstance(coverage, Mapping) else None,
        "acceptance_receipt_row_count": coverage.get("acceptance_receipt_row_count") if isinstance(coverage, Mapping) else None,
        "named_site_smoke_gate_row_count": coverage.get("named_site_smoke_gate_row_count") if isinstance(coverage, Mapping) else None,
        "handoff_status": handoff.get("handoff_status") if isinstance(handoff, Mapping) else None,
    }
