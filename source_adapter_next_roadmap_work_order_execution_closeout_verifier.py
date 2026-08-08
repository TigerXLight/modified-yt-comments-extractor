from __future__ import annotations

from typing import Any, Mapping

from source_adapter_next_roadmap_work_order_execution_closeout import HANDOFF_STATUS, SCHEMA_VERSION, STATUS

VERIFIER_SCHEMA_VERSION = "source_adapter_next_roadmap_work_order_execution_closeout_verifier_v1"


def _issue(issue_id: str, message: str, severity: str = "error") -> dict[str, str]:
    return {"issue_id": issue_id, "severity": severity, "message": message}


def verify_source_adapter_next_roadmap_work_order_execution_closeout(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    if package.get("schema_version") != SCHEMA_VERSION:
        issues.append(_issue("unexpected_schema", "package schema was not recognised"))
    if package.get("next_roadmap_work_order_execution_closeout_status") != STATUS:
        issues.append(_issue("unexpected_status", "work order execution closeout status is not built"))
    closeout_id = package.get("source_adapter_next_roadmap_work_order_execution_closeout_id")
    if not closeout_id:
        issues.append(_issue("missing_closeout_id", "closeout id is required"))
    if package.get("issue_count") != len(package.get("issues") or []):
        issues.append(_issue("issue_count_mismatch", "issue_count must match issues length"))

    execution_index = package.get("source_adapter_next_roadmap_work_order_execution_index") or {}
    execution_rows = execution_index.get("execution_rows") or []
    if not execution_rows:
        issues.append(_issue("missing_execution_rows", "work order execution rows are required"))
    if execution_index.get("executed_work_order_count") != len(execution_rows):
        issues.append(_issue("execution_rows_not_all_ready", "all work order execution rows must be executed"))

    gui_manifest = package.get("source_adapter_runtime_gui_controller_hardening_manifest") or {}
    provider_manifest = package.get("source_adapter_provider_execution_activation_manifest") or {}
    fixture_manifest = package.get("source_adapter_priority_fixture_pack_authoring_manifest") or {}
    live_smoke_manifest = package.get("source_adapter_live_smoke_receipt_capture_manifest") or {}
    regression_manifest = package.get("source_adapter_regular_regression_promotion_manifest") or {}
    doc_manifest = package.get("source_adapter_documentation_handoff_refresh_manifest") or {}
    handoff = package.get("source_adapter_next_roadmap_execution_ready_handoff") or {}

    if gui_manifest.get("keys_accounts_label") != "KEYS/ACCOUNTS":
        issues.append(_issue("keys_accounts_label_missing", "GUI manifest must preserve KEYS/ACCOUNTS label"))
    if gui_manifest.get("route_count", 0) < 4:
        issues.append(_issue("route_count_too_low", "GUI/controller manifest must include runtime, fixture, live-smoke, and KEYS/ACCOUNTS routes"))
    if provider_manifest.get("provider_activation_count", 0) < 4:
        issues.append(_issue("provider_activation_count_too_low", "provider activation manifest must include the expected provider adapters"))
    if fixture_manifest.get("fixture_pack_count", 0) < 5:
        issues.append(_issue("fixture_pack_count_too_low", "priority fixture pack manifest must include all five fixture families"))
    if live_smoke_manifest.get("live_smoke_receipt_capture_count", 0) < provider_manifest.get("provider_activation_count", 0):
        issues.append(_issue("live_smoke_rows_missing", "live smoke receipt capture rows must cover provider activation rows"))
    if regression_manifest.get("regression_promotion_count", 0) != len(execution_rows):
        issues.append(_issue("regression_count_mismatch", "regression promotion rows must match work order execution rows"))
    if doc_manifest.get("documentation_refresh_count", 0) < 4:
        issues.append(_issue("documentation_refresh_count_too_low", "documentation refresh manifest must include roadmap, state, runbook, and Codex queue rows"))
    if handoff.get("handoff_status") != HANDOFF_STATUS:
        issues.append(_issue("handoff_not_ready", "execution ready handoff is not ready"))
    for flag in (
        "ready_for_gui_controller_implementation_patch",
        "ready_for_provider_execution_activation_patch",
        "ready_for_priority_fixture_pack_authoring_patch",
        "ready_for_operator_approved_live_smoke_receipt_capture",
        "ready_for_regular_regression_promotion",
        "ready_for_documentation_handoff_refresh",
    ):
        if handoff.get(flag) is not True:
            issues.append(_issue(f"{flag}_not_ready", f"handoff flag {flag} is not ready"))

    return {
        "schema_version": VERIFIER_SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_next_roadmap_work_order_execution_closeout_id": closeout_id,
        "handoff_status": handoff.get("handoff_status"),
        "work_order_execution_count": len(execution_rows),
        "provider_activation_count": provider_manifest.get("provider_activation_count", 0),
        "fixture_pack_count": fixture_manifest.get("fixture_pack_count", 0),
        "live_smoke_receipt_capture_count": live_smoke_manifest.get("live_smoke_receipt_capture_count", 0),
        "regression_promotion_count": regression_manifest.get("regression_promotion_count", 0),
    }
