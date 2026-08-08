from __future__ import annotations

from typing import Any, Mapping

from source_adapter_next_roadmap_section_selection_closeout import (
    HANDOFF_STATUS,
    SCHEMA_VERSION,
    STATUS,
)

VERIFIER_SCHEMA_VERSION = "source_adapter_next_roadmap_section_selection_closeout_verifier_v1"


def verify_source_adapter_next_roadmap_section_selection_closeout(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if package.get("schema_version") != SCHEMA_VERSION:
        issues.append({"issue_id": "unexpected_schema", "severity": "error", "message": "next roadmap section selection closeout schema was not recognised"})
    if package.get("next_roadmap_section_selection_closeout_status") != STATUS:
        issues.append({"issue_id": "unexpected_status", "severity": "error", "message": "next roadmap section selection closeout is not built"})
    section_index = package.get("source_adapter_next_roadmap_section_selection_index") or {}
    work_orders = package.get("source_adapter_next_roadmap_work_order_manifest") or {}
    prompt_queue = package.get("source_adapter_next_roadmap_codex_prompt_queue") or {}
    regression_manifest = package.get("source_adapter_next_roadmap_regression_command_manifest") or {}
    handoff = package.get("source_adapter_next_roadmap_ready_handoff") or {}
    if section_index.get("section_selection_status") != "SOURCE_ADAPTER_NEXT_ROADMAP_SECTIONS_SELECTED":
        issues.append({"issue_id": "sections_not_selected", "severity": "error", "message": "next roadmap sections were not selected"})
    if work_orders.get("work_order_manifest_status") != "SOURCE_ADAPTER_NEXT_ROADMAP_WORK_ORDERS_READY":
        issues.append({"issue_id": "work_orders_not_ready", "severity": "error", "message": "next roadmap work orders are not ready"})
    if prompt_queue.get("codex_prompt_queue_status") != "SOURCE_ADAPTER_CODEX_PROMPT_QUEUE_READY":
        issues.append({"issue_id": "prompt_queue_not_ready", "severity": "error", "message": "Codex prompt queue is not ready"})
    if regression_manifest.get("regression_command_manifest_status") != "SOURCE_ADAPTER_NEXT_ROADMAP_REGRESSION_COMMANDS_READY":
        issues.append({"issue_id": "regression_commands_not_ready", "severity": "error", "message": "regression command manifest is not ready"})
    if handoff.get("handoff_status") != HANDOFF_STATUS:
        issues.append({"issue_id": "handoff_not_ready", "severity": "error", "message": "next roadmap ready handoff is not ready"})
    for flag in (
        "ready_for_next_largest_stable_patch",
        "ready_for_codex_mega_prompt_queue",
        "ready_for_regression_command_authoring",
    ):
        if handoff.get(flag) is not True:
            issues.append({"issue_id": f"{flag}_not_ready", "severity": "error", "message": f"handoff flag {flag} is not ready"})
    if (package.get("operator_summary") or {}).get("keys_accounts_label") != "KEYS/ACCOUNTS":
        issues.append({"issue_id": "keys_accounts_label_missing", "severity": "error", "message": "KEYS/ACCOUNTS label was not preserved"})
    if package.get("issue_count") not in (0, None):
        issues.append({"issue_id": "package_reported_issues", "severity": "error", "message": "package reported unresolved issues"})
    return {
        "schema_version": VERIFIER_SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_next_roadmap_section_selection_closeout_id": package.get("source_adapter_next_roadmap_section_selection_closeout_id"),
        "handoff_status": handoff.get("handoff_status"),
        "selected_section_count": section_index.get("selected_section_count", 0),
        "work_order_count": work_orders.get("work_order_count", 0),
        "prompt_row_count": prompt_queue.get("prompt_row_count", 0),
        "regression_command_row_count": regression_manifest.get("command_row_count", 0),
    }


def main() -> None:
    from source_adapter_next_roadmap_section_selection_closeout import example_next_roadmap_section_selection_closeout_package

    result = verify_source_adapter_next_roadmap_section_selection_closeout(example_next_roadmap_section_selection_closeout_package())
    assert result["verified"] is True
    assert result["handoff_status"] == HANDOFF_STATUS
    assert result["work_order_count"] >= 1
    print("Source Adapter Next Roadmap Section Selection Closeout verifier self-test passed.")


if __name__ == "__main__":
    main()
