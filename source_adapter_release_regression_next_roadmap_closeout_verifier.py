from __future__ import annotations

from typing import Any, Mapping

from source_adapter_release_regression_next_roadmap_closeout import (
    HANDOFF_STATUS,
    SCHEMA_VERSION,
    STATUS,
)

VERIFIER_SCHEMA_VERSION = "source_adapter_release_regression_next_roadmap_closeout_verifier_v1"


def verify_source_adapter_release_regression_next_roadmap_closeout(package: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if package.get("schema_version") != SCHEMA_VERSION:
        issues.append({"issue_id": "unexpected_schema", "severity": "error", "message": "release regression next roadmap closeout schema was not recognised"})
    if package.get("release_regression_next_roadmap_closeout_status") != STATUS:
        issues.append({"issue_id": "unexpected_status", "severity": "error", "message": "release regression next roadmap closeout is not built"})
    release_manifest = package.get("source_adapter_release_notes_manifest") or {}
    regression_queue = package.get("source_adapter_regular_regression_promotion_queue") or {}
    live_monitor = package.get("source_adapter_operator_live_execution_monitor_manifest") or {}
    handoff = package.get("source_adapter_next_roadmap_handoff") or {}
    if release_manifest.get("release_notes_status") != "SOURCE_ADAPTER_RELEASE_NOTES_READY":
        issues.append({"issue_id": "release_notes_not_ready", "severity": "error", "message": "release notes manifest is not ready"})
    if regression_queue.get("regular_regression_promotion_status") != "SOURCE_ADAPTER_REGRESSION_PROMOTION_QUEUE_READY":
        issues.append({"issue_id": "regression_queue_not_ready", "severity": "error", "message": "regular regression promotion queue is not ready"})
    if live_monitor.get("operator_live_execution_monitor_status") != "SOURCE_ADAPTER_OPERATOR_LIVE_EXECUTION_MONITOR_READY":
        issues.append({"issue_id": "live_monitor_not_ready", "severity": "error", "message": "operator live execution monitor manifest is not ready"})
    if handoff.get("handoff_status") != HANDOFF_STATUS:
        issues.append({"issue_id": "handoff_not_ready", "severity": "error", "message": "next roadmap handoff is not ready"})
    if handoff.get("ready_for_next_source_evidence_roadmap_section") is not True:
        issues.append({"issue_id": "next_roadmap_flag_missing", "severity": "error", "message": "next roadmap ready flag is missing"})
    if (package.get("operator_summary") or {}).get("keys_accounts_label") != "KEYS/ACCOUNTS":
        issues.append({"issue_id": "keys_accounts_label_missing", "severity": "error", "message": "KEYS/ACCOUNTS label was not preserved"})
    if package.get("issue_count") not in (0, None):
        issues.append({"issue_id": "package_reported_issues", "severity": "error", "message": "package reported unresolved issues"})
    return {
        "schema_version": VERIFIER_SCHEMA_VERSION,
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "source_adapter_release_regression_next_roadmap_closeout_id": package.get("source_adapter_release_regression_next_roadmap_closeout_id"),
        "handoff_status": handoff.get("handoff_status"),
        "release_note_section_count": release_manifest.get("section_count", 0),
        "regression_queue_row_count": regression_queue.get("queue_row_count", 0),
        "live_monitor_row_count": live_monitor.get("monitor_row_count", 0),
    }


def main() -> None:
    from source_adapter_release_regression_next_roadmap_closeout import example_release_regression_next_roadmap_closeout_package

    result = verify_source_adapter_release_regression_next_roadmap_closeout(example_release_regression_next_roadmap_closeout_package())
    assert result["verified"] is True
    assert result["handoff_status"] == HANDOFF_STATUS
    print("Source Adapter Release Regression Next Roadmap Closeout verifier self-test passed.")


if __name__ == "__main__":
    main()
