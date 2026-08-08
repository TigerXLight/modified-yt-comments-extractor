from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from source_adapter_operator_named_site_smoke_execution_closeout import (
    HANDOFF_STATUS as OPERATOR_NAMED_SITE_HANDOFF_STATUS,
    STATUS as OPERATOR_NAMED_SITE_STATUS,
    example_operator_named_site_smoke_execution_closeout_package,
)

SCHEMA_VERSION = "source_adapter_roadmap_audit_final_closeout_v1"
COMPLETION_INDEX_SCHEMA_VERSION = "source_adapter_roadmap_completion_index_v1"
REGRESSION_PROMOTION_SCHEMA_VERSION = "source_adapter_regression_promotion_manifest_v1"
LIVE_EXECUTION_ACCEPTANCE_SCHEMA_VERSION = "source_adapter_live_execution_acceptance_manifest_v1"
MASTER_AUDIT_SCHEMA_VERSION = "source_adapter_master_coverage_audit_closeout_v1"
FINAL_HANDOFF_SCHEMA_VERSION = "source_adapter_final_release_handoff_v1"
OPERATOR_SUMMARY_SCHEMA_VERSION = "source_adapter_roadmap_audit_final_closeout_operator_summary_v1"

STATUS = "SOURCE_ADAPTER_ROADMAP_AUDIT_FINAL_CLOSEOUT_BUILT"
HANDOFF_STATUS = "SOURCE_ADAPTER_SHARED_RUNTIME_SYSTEM_READY_FOR_RELEASE_NOTES_AND_OPERATOR_MONITORED_LIVE_EXECUTION"
BLOCKED_STATUS = "SOURCE_ADAPTER_ROADMAP_AUDIT_FINAL_CLOSEOUT_BLOCKED"

REQUIRED_ROADMAP_SECTIONS = [
    "source_adapter_coverage_framework",
    "source_adapter_fixture_matrix",
    "source_adapter_fixture_authoring",
    "source_adapter_fixture_review",
    "source_adapter_fixture_pipeline",
    "source_adapter_fixture_pipeline_closeout",
    "source_adapter_source_selection",
    "source_adapter_capture_setup",
    "source_adapter_capture_action_kit",
    "source_adapter_capture_session",
    "source_adapter_artifact_intake",
    "source_adapter_extraction_bridge",
    "source_adapter_capture_bundle_bridge",
    "source_adapter_total_export_bridge",
    "source_adapter_evidence_queue_bridge",
    "source_adapter_evidence_review_bridge",
    "source_adapter_approved_release_bridge",
    "source_adapter_release_index_bridge",
    "source_adapter_release_audit_bridge",
    "source_adapter_archive_handoff_bridge",
    "source_adapter_archive_result_intake_bridge",
    "source_adapter_archive_review_bridge",
    "source_adapter_pipeline_closeout_bridge",
    "source_adapter_runtime_wiring_bridge",
    "source_adapter_runtime_receipt_review_bridge",
    "source_adapter_runtime_ui_provider_integration_bridge",
    "source_adapter_runtime_operator_acceptance_closeout",
    "source_adapter_runtime_controller_provider_closeout",
    "source_adapter_runtime_fixture_smoke_final_closeout",
    "source_adapter_priority_site_pack_execution_closeout",
    "source_adapter_operator_named_site_smoke_execution_closeout",
]

DEFAULT_RELEASE_NOTE_TOPICS = [
    "Shared source adapter pipeline now routes multiple source families through common artifact, extraction, review, release, archive, runtime and smoke contracts.",
    "Priority site packs cover article/news pages, social post/thread sources, comments threads, media/transcript inputs and archive provider receipts.",
    "Runtime actions are represented with approval IDs, controller routes, provider adapter IDs, receipt fields and dry-run/operator-approved execution records.",
    "KEYS/ACCOUNTS credential references are preserved as redacted reference metadata rather than raw secret material.",
]

FINAL_OPERATOR_NEXT_ACTIONS = [
    "Promote accepted named-site fixture manifests into regular regression coverage.",
    "Attach operator-approved manual/live smoke receipts only for named site rows with captured provider receipts.",
    "Keep KEYS/ACCOUNTS references redacted in runtime and provider receipts.",
    "Use this final audit bundle as the source-adapter release note and next-roadmap handoff anchor.",
]


@dataclass(frozen=True)
class SourceAdapterRoadmapAuditFinalCloseout:
    package: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return deepcopy(self.package)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def short_hash(value: Any, length: int = 12) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()[:length]


def stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}.{short_hash(value)}"


def as_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    return dict(value)


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


def _validate_input(operator_closeout: Mapping[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if operator_closeout.get("schema_version") != "source_adapter_operator_named_site_smoke_execution_closeout_v1":
        issues.append({"issue_id": "unexpected_schema", "severity": "error", "message": "operator named-site smoke execution closeout schema was not recognised"})
    if operator_closeout.get("operator_named_site_smoke_execution_closeout_status") != OPERATOR_NAMED_SITE_STATUS:
        issues.append({"issue_id": "unexpected_status", "severity": "error", "message": "operator named-site smoke execution closeout is not built"})
    handoff = operator_closeout.get("source_adapter_operator_named_site_smoke_execution_handoff") or {}
    if handoff.get("handoff_status") != OPERATOR_NAMED_SITE_HANDOFF_STATUS:
        issues.append({"issue_id": "handoff_not_ready", "severity": "error", "message": "operator named-site smoke execution handoff is not ready for final roadmap audit"})
    if handoff.get("ready_for_source_evidence_roadmap_final_audit") is not True:
        issues.append({"issue_id": "final_audit_not_ready", "severity": "error", "message": "operator named-site smoke execution package is not marked ready for final roadmap audit"})
    return issues


def _extract_local_rows(operator_closeout: Mapping[str, Any]) -> list[dict[str, Any]]:
    batch = operator_closeout.get("source_adapter_operator_named_site_local_fixture_execution_batch") or {}
    return [dict(row) for row in as_list(batch.get("local_fixture_execution_rows"), "local_fixture_execution_rows") if isinstance(row, Mapping)]


def _extract_manual_rows(operator_closeout: Mapping[str, Any]) -> list[dict[str, Any]]:
    batch = operator_closeout.get("source_adapter_operator_named_site_manual_smoke_execution_batch") or {}
    return [dict(row) for row in as_list(batch.get("manual_smoke_execution_rows"), "manual_smoke_execution_rows") if isinstance(row, Mapping)]


def _extract_acceptance_index(operator_closeout: Mapping[str, Any]) -> dict[str, Any]:
    return dict(operator_closeout.get("source_adapter_operator_named_site_receipt_acceptance_index") or {})


def _extract_closed_sections(operator_closeout: Mapping[str, Any], roadmap_sections: Sequence[str] | None) -> list[str]:
    sections = list(REQUIRED_ROADMAP_SECTIONS)
    roadmap_closeout = operator_closeout.get("source_adapter_operator_named_site_roadmap_final_closeout") or {}
    for section in _strings(roadmap_closeout.get("closed_sections") or []):
        if section not in sections:
            sections.append(section)
    for section in _strings(roadmap_sections or []):
        if section not in sections:
            sections.append(section)
    return sections


def _build_completion_index(operator_closeout: Mapping[str, Any], roadmap_sections: Sequence[str] | None, issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    closed_sections = _extract_closed_sections(operator_closeout, roadmap_sections)
    missing_sections = [section for section in REQUIRED_ROADMAP_SECTIONS if section not in closed_sections]
    status = "SOURCE_ADAPTER_ROADMAP_REQUIRED_SECTIONS_CLOSED" if not issues and not missing_sections else "SOURCE_ADAPTER_ROADMAP_REQUIRED_SECTIONS_NEED_REVIEW"
    return {
        "schema_version": COMPLETION_INDEX_SCHEMA_VERSION,
        "completion_status": status,
        "required_section_count": len(REQUIRED_ROADMAP_SECTIONS),
        "closed_section_count": len(closed_sections),
        "required_sections": list(REQUIRED_ROADMAP_SECTIONS),
        "closed_sections": closed_sections,
        "missing_sections": missing_sections,
        "operator_named_site_smoke_execution_closeout_id": operator_closeout.get("source_adapter_operator_named_site_smoke_execution_closeout_id"),
        "shared_adapter_pipeline_closed": not missing_sections,
        "runtime_acceptance_closed": all(section in closed_sections for section in REQUIRED_ROADMAP_SECTIONS[-8:]),
        "priority_site_pack_acceptance_closed": "source_adapter_operator_named_site_smoke_execution_closeout" in closed_sections,
    }


def _build_regression_promotion_manifest(local_rows: Sequence[Mapping[str, Any]], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    promotion_rows: list[dict[str, Any]] = []
    for index, row in enumerate(local_rows):
        accepted = row.get("local_fixture_execution_status") in {
            "LOCAL_FIXTURE_EXECUTION_ACCEPTED",
            "SOURCE_ADAPTER_OPERATOR_NAMED_SITE_LOCAL_FIXTURE_ACCEPTED",
            "SOURCE_ADAPTER_OPERATOR_NAMED_SITE_LOCAL_FIXTURES_ACCEPTED",
        } or row.get("missing_fixture_files") in ([], None)
        seed = {
            "row_id": row.get("operator_named_site_local_fixture_execution_row_id"),
            "site_pack_id": row.get("site_pack_id"),
            "source_url": row.get("source_url"),
            "index": index,
        }
        promotion_rows.append(
            {
                "schema_version": "source_adapter_regression_promotion_row_v1",
                "row_index": index,
                "regression_promotion_row_id": stable_id("source_adapter.regression_promotion", seed),
                "operator_named_site_local_fixture_execution_row_id": row.get("operator_named_site_local_fixture_execution_row_id"),
                "site_pack_id": row.get("site_pack_id"),
                "operator_named_site_id": row.get("operator_named_site_id"),
                "source_url": row.get("source_url"),
                "fixture_manifest_id": row.get("fixture_manifest_id"),
                "fixture_root": row.get("fixture_root"),
                "expected_pipeline_stage_count": len(_strings(row.get("expected_pipeline_stages") or [])),
                "promotion_target": "regular_source_adapter_regression_tail",
                "promotion_status": "READY_FOR_REGRESSION_PROMOTION" if accepted and not issues else "NEEDS_FIXTURE_OR_RECEIPT_REVIEW",
            }
        )
    ready_count = sum(1 for row in promotion_rows if row["promotion_status"] == "READY_FOR_REGRESSION_PROMOTION")
    return {
        "schema_version": REGRESSION_PROMOTION_SCHEMA_VERSION,
        "regression_promotion_status": "SOURCE_ADAPTER_NAMED_SITE_FIXTURES_READY_FOR_REGRESSION_PROMOTION" if ready_count == len(promotion_rows) and promotion_rows else "SOURCE_ADAPTER_NAMED_SITE_FIXTURES_NEED_REVIEW",
        "promotion_row_count": len(promotion_rows),
        "ready_promotion_row_count": ready_count,
        "promotion_rows": promotion_rows,
    }


def _manual_receipt_accepted(row: Mapping[str, Any]) -> bool:
    if row.get("missing_receipt_fields") not in ([], None):
        return False
    receipt = row.get("manual_smoke_receipt") or row.get("provider_receipt") or {}
    if isinstance(receipt, Mapping) and str(receipt.get("receipt_status") or "").strip():
        return True
    status = str(row.get("receipt_acceptance_status") or row.get("manual_smoke_execution_status") or "").upper()
    return "ACCEPTED" in status or "RECORDED" in status


def _build_live_execution_acceptance_manifest(manual_rows: Sequence[Mapping[str, Any]], acceptance_index: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    live_rows: list[dict[str, Any]] = []
    for index, row in enumerate(manual_rows):
        accepted = _manual_receipt_accepted(row)
        seed = {
            "row_id": row.get("operator_named_site_manual_smoke_execution_row_id"),
            "scenario": row.get("manual_smoke_scenario_id"),
            "index": index,
        }
        live_rows.append(
            {
                "schema_version": "source_adapter_live_execution_acceptance_row_v1",
                "row_index": index,
                "live_execution_acceptance_row_id": stable_id("source_adapter.live_execution_acceptance", seed),
                "operator_named_site_manual_smoke_execution_row_id": row.get("operator_named_site_manual_smoke_execution_row_id"),
                "manual_smoke_scenario_id": row.get("manual_smoke_scenario_id"),
                "operator_named_site_id": row.get("operator_named_site_id"),
                "site_pack_id": row.get("site_pack_id"),
                "capability_id": row.get("capability_id"),
                "provider_execution_adapter_id": row.get("provider_execution_adapter_id"),
                "controller_route_id": row.get("controller_route_id"),
                "receipt_capture_required": True,
                "receipt_accepted_for_audit": accepted and not issues,
                "keys_accounts_reference_used": bool(row.get("credential_reference_id") or row.get("redacted_reference_hash") or row.get("keys_accounts_reference_used")),
                "live_execution_acceptance_status": "ACCEPTED_FOR_OPERATOR_MONITORED_LIVE_EXECUTION" if accepted and not issues else "NEEDS_PROVIDER_RECEIPT_ATTACHMENT_OR_REVIEW",
            }
        )
    accepted_count = sum(1 for row in live_rows if row["receipt_accepted_for_audit"])
    keys_ok = acceptance_index.get("keys_accounts_redacted_credential_references_ok") is not False
    return {
        "schema_version": LIVE_EXECUTION_ACCEPTANCE_SCHEMA_VERSION,
        "live_execution_acceptance_status": "SOURCE_ADAPTER_OPERATOR_APPROVED_LIVE_EXECUTION_RECEIPTS_ACCEPTED" if accepted_count == len(live_rows) and live_rows and keys_ok else "SOURCE_ADAPTER_OPERATOR_APPROVED_LIVE_EXECUTION_RECEIPTS_NEED_REVIEW",
        "live_execution_row_count": len(live_rows),
        "accepted_live_execution_row_count": accepted_count,
        "keys_accounts_redacted_credential_references_ok": keys_ok,
        "live_execution_rows": live_rows,
    }


def _build_master_audit_closeout(completion_index: Mapping[str, Any], regression_manifest: Mapping[str, Any], live_manifest: Mapping[str, Any], release_notes: Sequence[str] | None, issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ready = (
        not issues
        and completion_index.get("completion_status") == "SOURCE_ADAPTER_ROADMAP_REQUIRED_SECTIONS_CLOSED"
        and regression_manifest.get("regression_promotion_status") == "SOURCE_ADAPTER_NAMED_SITE_FIXTURES_READY_FOR_REGRESSION_PROMOTION"
        and live_manifest.get("live_execution_acceptance_status") == "SOURCE_ADAPTER_OPERATOR_APPROVED_LIVE_EXECUTION_RECEIPTS_ACCEPTED"
    )
    notes = _strings(release_notes or DEFAULT_RELEASE_NOTE_TOPICS)
    return {
        "schema_version": MASTER_AUDIT_SCHEMA_VERSION,
        "master_audit_closeout_status": "SOURCE_ADAPTER_MASTER_COVERAGE_AUDIT_CLOSED" if ready else "SOURCE_ADAPTER_MASTER_COVERAGE_AUDIT_NEEDS_REVIEW",
        "coverage_audit_closed": ready,
        "source_evidence_roadmap_section": "shared_source_adapter_runtime_and_priority_site_pack_system",
        "closed_section_count": completion_index.get("closed_section_count", 0),
        "required_section_count": completion_index.get("required_section_count", 0),
        "regression_promotion_row_count": regression_manifest.get("promotion_row_count", 0),
        "live_execution_row_count": live_manifest.get("live_execution_row_count", 0),
        "keys_accounts_label": "KEYS/ACCOUNTS",
        "keys_accounts_lookup_surface": "keys_accounts.ui.credential_reference_selector",
        "credential_secret_material_policy": "redacted_reference_metadata_only",
        "release_note_topics": notes,
        "remaining_operator_actions": [
            "promote accepted named-site fixture rows into the regular regression tail",
            "attach future provider receipts to accepted operator-named smoke rows",
            "run additional named sites through the same shared adapter contracts",
        ],
    }


def _build_final_handoff(closeout_id: str, completion_index: Mapping[str, Any], regression_manifest: Mapping[str, Any], live_manifest: Mapping[str, Any], master_audit: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ready = not issues and master_audit.get("coverage_audit_closed") is True
    return {
        "schema_version": FINAL_HANDOFF_SCHEMA_VERSION,
        "handoff_status": HANDOFF_STATUS if ready else BLOCKED_STATUS,
        "source_adapter_roadmap_audit_final_closeout_id": closeout_id,
        "ready_for_release_notes": ready,
        "ready_for_regular_regression_promotion": ready,
        "ready_for_operator_monitored_live_execution": ready,
        "ready_for_next_source_evidence_roadmap_section": ready,
        "required_next_stage": "release_notes_regular_regression_and_next_roadmap_section" if ready else "roadmap_audit_receipt_or_fixture_repair",
        "closed_section_count": completion_index.get("closed_section_count", 0),
        "promotion_row_count": regression_manifest.get("promotion_row_count", 0),
        "live_execution_row_count": live_manifest.get("live_execution_row_count", 0),
        "master_audit_closeout_status": master_audit.get("master_audit_closeout_status"),
    }


def build_source_adapter_roadmap_audit_final_closeout(
    operator_named_site_smoke_execution_closeout_package: Mapping[str, Any],
    *,
    roadmap_sections: Sequence[str] | None = None,
    release_notes: Sequence[str] | None = None,
    operator_id: str = "operator",
    closeout_notes: Sequence[str] | None = None,
) -> SourceAdapterRoadmapAuditFinalCloseout:
    operator_closeout = as_mapping(operator_named_site_smoke_execution_closeout_package, "operator_named_site_smoke_execution_closeout_package")
    issues = _validate_input(operator_closeout)
    local_rows = _extract_local_rows(operator_closeout)
    manual_rows = _extract_manual_rows(operator_closeout)
    acceptance_index = _extract_acceptance_index(operator_closeout)
    if not local_rows:
        issues.append({"issue_id": "missing_local_fixture_execution_rows", "severity": "error", "message": "local fixture execution rows are required for final roadmap audit"})
    if not manual_rows:
        issues.append({"issue_id": "missing_manual_smoke_execution_rows", "severity": "error", "message": "manual smoke execution rows are required for final roadmap audit"})
    if acceptance_index.get("receipt_acceptance_status") not in ("SOURCE_ADAPTER_OPERATOR_NAMED_SITE_RECEIPTS_ACCEPTED", None):
        issues.append({"issue_id": "receipt_acceptance_index_not_accepted", "severity": "error", "message": "operator named-site receipt acceptance index is not accepted"})
    completion_index = _build_completion_index(operator_closeout, roadmap_sections, issues)
    regression_manifest = _build_regression_promotion_manifest(local_rows, issues)
    live_manifest = _build_live_execution_acceptance_manifest(manual_rows, acceptance_index, issues)
    master_audit = _build_master_audit_closeout(completion_index, regression_manifest, live_manifest, release_notes, issues)
    closeout_seed = {
        "operator_closeout_id": operator_closeout.get("source_adapter_operator_named_site_smoke_execution_closeout_id"),
        "operator_id": operator_id,
        "closed_sections": completion_index.get("closed_sections"),
        "promotion_rows": regression_manifest.get("promotion_row_count"),
        "live_rows": live_manifest.get("live_execution_row_count"),
    }
    closeout_id = stable_id("source_adapter.roadmap_audit_final_closeout", closeout_seed)
    handoff = _build_final_handoff(closeout_id, completion_index, regression_manifest, live_manifest, master_audit, issues)
    ready = handoff.get("handoff_status") == HANDOFF_STATUS
    operator_summary = {
        "schema_version": OPERATOR_SUMMARY_SCHEMA_VERSION,
        "status": STATUS if ready else BLOCKED_STATUS,
        "closed_section_count": completion_index.get("closed_section_count", 0),
        "promotion_row_count": regression_manifest.get("promotion_row_count", 0),
        "live_execution_row_count": live_manifest.get("live_execution_row_count", 0),
        "keys_accounts_label": "KEYS/ACCOUNTS",
        "next_actions": list(FINAL_OPERATOR_NEXT_ACTIONS),
    }
    package = {
        "schema_version": SCHEMA_VERSION,
        "roadmap_audit_final_closeout_status": STATUS if ready else BLOCKED_STATUS,
        "source_adapter_roadmap_audit_final_closeout_id": closeout_id,
        "source_adapter_operator_named_site_smoke_execution_closeout_id": operator_closeout.get("source_adapter_operator_named_site_smoke_execution_closeout_id"),
        "operator_id": str(operator_id),
        "issue_count": len(issues),
        "issues": issues,
        "closeout_notes": _strings(closeout_notes or []),
        "implementation_logic": {
            "input_source": "source_adapter_operator_named_site_smoke_execution_closeout",
            "master_coverage_audit_closeout_built": True,
            "regression_promotion_manifest_built": True,
            "operator_live_execution_acceptance_manifest_built": True,
            "release_handoff_built": True,
            "keys_accounts_label_preserved": True,
            "multi_named_site_batch_supported": True,
        },
        "source_adapter_roadmap_completion_index": completion_index,
        "source_adapter_regression_promotion_manifest": regression_manifest,
        "source_adapter_live_execution_acceptance_manifest": live_manifest,
        "source_adapter_master_coverage_audit_closeout": master_audit,
        "source_adapter_final_release_handoff": handoff,
        "operator_summary": operator_summary,
    }
    return SourceAdapterRoadmapAuditFinalCloseout(package)


def example_roadmap_audit_final_closeout_package() -> dict[str, Any]:
    return build_source_adapter_roadmap_audit_final_closeout(
        example_operator_named_site_smoke_execution_closeout_package(),
        operator_id="example_operator",
    ).as_dict()


def main() -> None:
    package = example_roadmap_audit_final_closeout_package()
    assert package["schema_version"] == SCHEMA_VERSION
    assert package["roadmap_audit_final_closeout_status"] == STATUS
    assert package["source_adapter_final_release_handoff"]["handoff_status"] == HANDOFF_STATUS
    assert package["source_adapter_master_coverage_audit_closeout"]["keys_accounts_label"] == "KEYS/ACCOUNTS"
    assert package["source_adapter_roadmap_completion_index"]["closed_section_count"] >= len(REQUIRED_ROADMAP_SECTIONS)
    print("Source Adapter Roadmap Audit Final Closeout self-test passed.")


if __name__ == "__main__":
    main()
