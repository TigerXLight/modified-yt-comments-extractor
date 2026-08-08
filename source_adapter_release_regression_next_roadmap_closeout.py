from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from source_adapter_roadmap_audit_final_closeout import (
    HANDOFF_STATUS as ROADMAP_AUDIT_HANDOFF_STATUS,
    STATUS as ROADMAP_AUDIT_STATUS,
    example_roadmap_audit_final_closeout_package,
)

SCHEMA_VERSION = "source_adapter_release_regression_next_roadmap_closeout_v1"
RELEASE_NOTES_SCHEMA_VERSION = "source_adapter_release_notes_manifest_v1"
REGRESSION_QUEUE_SCHEMA_VERSION = "source_adapter_regular_regression_promotion_queue_v1"
LIVE_MONITOR_SCHEMA_VERSION = "source_adapter_operator_live_execution_monitor_manifest_v1"
NEXT_ROADMAP_HANDOFF_SCHEMA_VERSION = "source_adapter_next_roadmap_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_release_regression_next_roadmap_operator_summary_v1"

STATUS = "SOURCE_ADAPTER_RELEASE_REGRESSION_NEXT_ROADMAP_CLOSEOUT_BUILT"
HANDOFF_STATUS = "SOURCE_ADAPTER_RELEASE_REGRESSION_AND_NEXT_ROADMAP_HANDOFF_READY"
BLOCKED_STATUS = "SOURCE_ADAPTER_RELEASE_REGRESSION_NEXT_ROADMAP_CLOSEOUT_BLOCKED"

DEFAULT_RELEASE_AUDIENCES = [
    "operator",
    "developer",
    "regression_runner",
    "release_notes_reader",
]

DEFAULT_NEXT_ACTIONS = [
    "Promote the queued source-adapter regression rows into the normal regression command set.",
    "Attach future operator-monitored live receipts to the accepted live execution monitor rows.",
    "Keep KEYS/ACCOUNTS credential values represented by redacted credential references in every receipt.",
    "Use the next-roadmap handoff as the anchor for the following Source Evidence roadmap section.",
]


@dataclass(frozen=True)
class SourceAdapterReleaseRegressionNextRoadmapCloseout:
    package: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return deepcopy(self.package)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def short_hash(value: Any, length: int = 12) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()[:length]


def stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}.{short_hash(value)}"


def as_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    return value


def as_list(value: Any, label: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise TypeError(f"{label} must be a list")
    return list(value)


def _strings(values: Iterable[Any]) -> list[str]:
    output: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in output:
            output.append(text)
    return output


def _validate_input(roadmap_audit_closeout: Mapping[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if roadmap_audit_closeout.get("schema_version") != "source_adapter_roadmap_audit_final_closeout_v1":
        issues.append({"issue_id": "unexpected_schema", "severity": "error", "message": "roadmap audit final closeout schema was not recognised"})
    if roadmap_audit_closeout.get("roadmap_audit_final_closeout_status") != ROADMAP_AUDIT_STATUS:
        issues.append({"issue_id": "unexpected_status", "severity": "error", "message": "roadmap audit final closeout is not built"})
    handoff = roadmap_audit_closeout.get("source_adapter_final_release_handoff") or {}
    if handoff.get("handoff_status") != ROADMAP_AUDIT_HANDOFF_STATUS:
        issues.append({"issue_id": "handoff_not_ready", "severity": "error", "message": "roadmap audit final closeout handoff is not ready"})
    for flag in (
        "ready_for_release_notes",
        "ready_for_regular_regression_promotion",
        "ready_for_operator_monitored_live_execution",
        "ready_for_next_source_evidence_roadmap_section",
    ):
        if handoff.get(flag) is not True:
            issues.append({"issue_id": f"{flag}_not_ready", "severity": "error", "message": f"final release handoff flag {flag} is not ready"})
    return issues


def _release_note_topics(roadmap_audit_closeout: Mapping[str, Any], extra_release_notes: Sequence[str] | None) -> list[str]:
    audit = roadmap_audit_closeout.get("source_adapter_master_coverage_audit_closeout") or {}
    topics = _strings(audit.get("release_note_topics") or [])
    for note in _strings(extra_release_notes or []):
        if note not in topics:
            topics.append(note)
    return topics


def _build_release_notes_manifest(roadmap_audit_closeout: Mapping[str, Any], release_notes: Sequence[str] | None, commit_checkpoint: str | None, issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    topics = _release_note_topics(roadmap_audit_closeout, release_notes)
    completion = roadmap_audit_closeout.get("source_adapter_roadmap_completion_index") or {}
    audit = roadmap_audit_closeout.get("source_adapter_master_coverage_audit_closeout") or {}
    sections = [
        {
            "schema_version": "source_adapter_release_note_section_v1",
            "section_id": stable_id("source_adapter.release_note_section", {"topic": topic, "index": index}),
            "section_index": index,
            "topic": topic,
            "audiences": list(DEFAULT_RELEASE_AUDIENCES),
            "release_note_status": "READY_FOR_RELEASE_NOTES" if not issues else "NEEDS_AUDIT_REVIEW",
        }
        for index, topic in enumerate(topics)
    ]
    return {
        "schema_version": RELEASE_NOTES_SCHEMA_VERSION,
        "release_notes_status": "SOURCE_ADAPTER_RELEASE_NOTES_READY" if sections and not issues else "SOURCE_ADAPTER_RELEASE_NOTES_NEED_REVIEW",
        "source_adapter_roadmap_audit_final_closeout_id": roadmap_audit_closeout.get("source_adapter_roadmap_audit_final_closeout_id"),
        "commit_checkpoint": str(commit_checkpoint or "c063336"),
        "keys_accounts_label": audit.get("keys_accounts_label", "KEYS/ACCOUNTS"),
        "closed_section_count": completion.get("closed_section_count", 0),
        "section_count": len(sections),
        "release_note_sections": sections,
    }


def _build_regression_queue(roadmap_audit_closeout: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    manifest = roadmap_audit_closeout.get("source_adapter_regression_promotion_manifest") or {}
    promotion_rows = [dict(row) for row in as_list(manifest.get("promotion_rows"), "promotion_rows") if isinstance(row, Mapping)]
    queue_rows: list[dict[str, Any]] = []
    for index, row in enumerate(promotion_rows):
        ready = row.get("promotion_status") == "READY_FOR_REGRESSION_PROMOTION" and not issues
        seed = {
            "promotion_row_id": row.get("regression_promotion_row_id"),
            "site_pack_id": row.get("site_pack_id"),
            "index": index,
        }
        queue_rows.append(
            {
                "schema_version": "source_adapter_regular_regression_promotion_queue_row_v1",
                "row_index": index,
                "regression_queue_row_id": stable_id("source_adapter.regular_regression_queue", seed),
                "regression_promotion_row_id": row.get("regression_promotion_row_id"),
                "site_pack_id": row.get("site_pack_id"),
                "operator_named_site_id": row.get("operator_named_site_id"),
                "source_url": row.get("source_url"),
                "fixture_manifest_id": row.get("fixture_manifest_id"),
                "promotion_target": row.get("promotion_target", "regular_source_adapter_regression_tail"),
                "recommended_command_group": "source_adapter_priority_site_pack_regression_tail",
                "queue_status": "READY_FOR_REGULAR_REGRESSION_PROMOTION" if ready else "NEEDS_FIXTURE_REVIEW_BEFORE_PROMOTION",
            }
        )
    ready_count = sum(1 for row in queue_rows if row["queue_status"] == "READY_FOR_REGULAR_REGRESSION_PROMOTION")
    return {
        "schema_version": REGRESSION_QUEUE_SCHEMA_VERSION,
        "regular_regression_promotion_status": "SOURCE_ADAPTER_REGRESSION_PROMOTION_QUEUE_READY" if queue_rows and ready_count == len(queue_rows) else "SOURCE_ADAPTER_REGRESSION_PROMOTION_QUEUE_NEEDS_REVIEW",
        "queue_row_count": len(queue_rows),
        "ready_queue_row_count": ready_count,
        "queue_rows": queue_rows,
    }


def _build_live_monitor_manifest(roadmap_audit_closeout: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    live_manifest = roadmap_audit_closeout.get("source_adapter_live_execution_acceptance_manifest") or {}
    live_rows = [dict(row) for row in as_list(live_manifest.get("live_execution_rows"), "live_execution_rows") if isinstance(row, Mapping)]
    monitor_rows: list[dict[str, Any]] = []
    for index, row in enumerate(live_rows):
        accepted = row.get("receipt_accepted_for_audit") is True and not issues
        seed = {
            "live_row": row.get("live_execution_acceptance_row_id"),
            "capability": row.get("capability_id"),
            "index": index,
        }
        monitor_rows.append(
            {
                "schema_version": "source_adapter_operator_live_execution_monitor_row_v1",
                "row_index": index,
                "operator_live_execution_monitor_row_id": stable_id("source_adapter.operator_live_monitor", seed),
                "live_execution_acceptance_row_id": row.get("live_execution_acceptance_row_id"),
                "operator_named_site_manual_smoke_execution_row_id": row.get("operator_named_site_manual_smoke_execution_row_id"),
                "operator_named_site_id": row.get("operator_named_site_id"),
                "site_pack_id": row.get("site_pack_id"),
                "capability_id": row.get("capability_id"),
                "provider_execution_adapter_id": row.get("provider_execution_adapter_id"),
                "controller_route_id": row.get("controller_route_id"),
                "receipt_capture_required": True,
                "credential_secret_material_policy": "redacted_reference_metadata_only",
                "monitor_profile": "operator_monitored_receipt_capture",
                "monitor_status": "READY_FOR_OPERATOR_MONITORED_LIVE_EXECUTION" if accepted else "NEEDS_PROVIDER_RECEIPT_REVIEW_BEFORE_MONITORING",
            }
        )
    ready_count = sum(1 for row in monitor_rows if row["monitor_status"] == "READY_FOR_OPERATOR_MONITORED_LIVE_EXECUTION")
    return {
        "schema_version": LIVE_MONITOR_SCHEMA_VERSION,
        "operator_live_execution_monitor_status": "SOURCE_ADAPTER_OPERATOR_LIVE_EXECUTION_MONITOR_READY" if monitor_rows and ready_count == len(monitor_rows) else "SOURCE_ADAPTER_OPERATOR_LIVE_EXECUTION_MONITOR_NEEDS_REVIEW",
        "monitor_row_count": len(monitor_rows),
        "ready_monitor_row_count": ready_count,
        "monitor_rows": monitor_rows,
    }


def _build_next_roadmap_handoff(closeout_id: str, release_manifest: Mapping[str, Any], regression_queue: Mapping[str, Any], monitor_manifest: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ready = (
        not issues
        and release_manifest.get("release_notes_status") == "SOURCE_ADAPTER_RELEASE_NOTES_READY"
        and regression_queue.get("regular_regression_promotion_status") == "SOURCE_ADAPTER_REGRESSION_PROMOTION_QUEUE_READY"
        and monitor_manifest.get("operator_live_execution_monitor_status") == "SOURCE_ADAPTER_OPERATOR_LIVE_EXECUTION_MONITOR_READY"
    )
    return {
        "schema_version": NEXT_ROADMAP_HANDOFF_SCHEMA_VERSION,
        "handoff_status": HANDOFF_STATUS if ready else BLOCKED_STATUS,
        "source_adapter_release_regression_next_roadmap_closeout_id": closeout_id,
        "ready_for_release_notes_publication": ready,
        "ready_for_regular_regression_queue_integration": ready,
        "ready_for_operator_monitored_live_execution": ready,
        "ready_for_next_source_evidence_roadmap_section": ready,
        "required_next_stage": "source_evidence_next_roadmap_section_selection" if ready else "release_regression_or_live_monitor_review",
        "release_note_section_count": release_manifest.get("section_count", 0),
        "regression_queue_row_count": regression_queue.get("queue_row_count", 0),
        "live_monitor_row_count": monitor_manifest.get("monitor_row_count", 0),
    }


def build_source_adapter_release_regression_next_roadmap_closeout(
    roadmap_audit_final_closeout_package: Mapping[str, Any],
    *,
    release_notes: Sequence[str] | None = None,
    commit_checkpoint: str | None = None,
    operator_id: str = "operator",
    closeout_notes: Sequence[str] | None = None,
) -> SourceAdapterReleaseRegressionNextRoadmapCloseout:
    roadmap_closeout = as_mapping(roadmap_audit_final_closeout_package, "roadmap_audit_final_closeout_package")
    issues = _validate_input(roadmap_closeout)
    release_manifest = _build_release_notes_manifest(roadmap_closeout, release_notes, commit_checkpoint, issues)
    regression_queue = _build_regression_queue(roadmap_closeout, issues)
    monitor_manifest = _build_live_monitor_manifest(roadmap_closeout, issues)
    seed = {
        "roadmap_closeout_id": roadmap_closeout.get("source_adapter_roadmap_audit_final_closeout_id"),
        "operator_id": operator_id,
        "release_sections": release_manifest.get("section_count"),
        "regression_rows": regression_queue.get("queue_row_count"),
        "monitor_rows": monitor_manifest.get("monitor_row_count"),
    }
    closeout_id = stable_id("source_adapter.release_regression_next_roadmap_closeout", seed)
    handoff = _build_next_roadmap_handoff(closeout_id, release_manifest, regression_queue, monitor_manifest, issues)
    ready = handoff.get("handoff_status") == HANDOFF_STATUS
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": STATUS if ready else BLOCKED_STATUS,
        "release_note_section_count": release_manifest.get("section_count", 0),
        "regression_queue_row_count": regression_queue.get("queue_row_count", 0),
        "live_monitor_row_count": monitor_manifest.get("monitor_row_count", 0),
        "keys_accounts_label": "KEYS/ACCOUNTS",
        "next_actions": list(DEFAULT_NEXT_ACTIONS),
    }
    package = {
        "schema_version": SCHEMA_VERSION,
        "release_regression_next_roadmap_closeout_status": STATUS if ready else BLOCKED_STATUS,
        "source_adapter_release_regression_next_roadmap_closeout_id": closeout_id,
        "source_adapter_roadmap_audit_final_closeout_id": roadmap_closeout.get("source_adapter_roadmap_audit_final_closeout_id"),
        "operator_id": str(operator_id),
        "issue_count": len(issues),
        "issues": issues,
        "closeout_notes": _strings(closeout_notes or []),
        "implementation_logic": {
            "input_source": "source_adapter_roadmap_audit_final_closeout",
            "release_notes_manifest_built": True,
            "regular_regression_promotion_queue_built": True,
            "operator_live_execution_monitor_manifest_built": True,
            "next_roadmap_handoff_built": True,
            "keys_accounts_label_preserved": True,
            "source_adapter_section_release_ready": ready,
        },
        "source_adapter_release_notes_manifest": release_manifest,
        "source_adapter_regular_regression_promotion_queue": regression_queue,
        "source_adapter_operator_live_execution_monitor_manifest": monitor_manifest,
        "source_adapter_next_roadmap_handoff": handoff,
        "operator_summary": operator_summary,
    }
    return SourceAdapterReleaseRegressionNextRoadmapCloseout(package)


def example_release_regression_next_roadmap_closeout_package() -> dict[str, Any]:
    return build_source_adapter_release_regression_next_roadmap_closeout(
        example_roadmap_audit_final_closeout_package(),
        commit_checkpoint="c063336",
        operator_id="example_operator",
    ).as_dict()


def main() -> None:
    package = example_release_regression_next_roadmap_closeout_package()
    assert package["schema_version"] == SCHEMA_VERSION
    assert package["release_regression_next_roadmap_closeout_status"] == STATUS
    assert package["source_adapter_next_roadmap_handoff"]["handoff_status"] == HANDOFF_STATUS
    assert package["operator_summary"]["keys_accounts_label"] == "KEYS/ACCOUNTS"
    assert package["source_adapter_regular_regression_promotion_queue"]["queue_row_count"] >= 1
    print("Source Adapter Release Regression Next Roadmap Closeout self-test passed.")


if __name__ == "__main__":
    main()
