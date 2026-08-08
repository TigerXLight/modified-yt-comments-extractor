from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = "source_adapter_priority_site_pack_execution_closeout_v1"
SITE_PACK_MATRIX_SCHEMA_VERSION = "source_adapter_priority_site_fixture_pack_matrix_v1"
LOCAL_FIXTURE_RUN_PLAN_SCHEMA_VERSION = "source_adapter_priority_site_local_fixture_run_plan_v1"
MANUAL_SMOKE_PLAN_SCHEMA_VERSION = "source_adapter_priority_site_manual_smoke_plan_v1"
ROADMAP_CLOSEOUT_SCHEMA_VERSION = "source_adapter_priority_site_roadmap_closeout_v1"
HANDOFF_SCHEMA_VERSION = "source_adapter_priority_site_pack_execution_handoff_v1"
OPERATOR_SUMMARY_SCHEMA_VERSION = "source_adapter_priority_site_pack_execution_closeout_operator_summary_v1"

STATUS = "SOURCE_ADAPTER_PRIORITY_SITE_PACK_EXECUTION_CLOSEOUT_BUILT"
HANDOFF_STATUS = "SOURCE_ADAPTER_PRIORITY_SITE_PACKS_READY_FOR_LOCAL_FIXTURES_AND_OPERATOR_APPROVED_SMOKE"
EXPECTED_INPUT_STATUS = "SOURCE_ADAPTER_RUNTIME_FIXTURE_SMOKE_FINAL_CLOSEOUT_BUILT"
EXPECTED_INPUT_HANDOFF_STATUS = "SOURCE_ADAPTER_RUNTIME_SHARED_SYSTEM_READY_FOR_PRIORITY_SITE_PACKS_AND_OPERATOR_APPROVED_SMOKE"

DEFAULT_PIPELINE_STAGES = [
    "artifact_collection",
    "content_or_comment_extraction",
    "capture_bundle",
    "total_export_package",
    "evidence_queue",
    "evidence_review",
    "approved_release",
    "release_index",
    "release_audit",
    "archive_handoff",
    "archive_result_intake",
    "archive_review",
    "pipeline_closeout",
    "runtime_receipt_capture",
]

DEFAULT_CAPABILITY_IDS = [
    "url_fetch_load",
    "browser_launch",
    "folder_scan",
    "credential_lookup",
    "archive_submit",
    "release_upload",
    "app_registry_mutation",
    "file_library_publication",
]

BASE_REQUIRED_FIXTURE_TYPES = [
    "source_artifact_file_or_text",
    "source_metadata_json",
    "expected_extraction_json",
    "expected_total_export_package_json",
    "expected_release_archive_closeout_json",
]

BASE_RECEIPT_FIELDS = [
    "runtime_action_execution_receipt_id",
    "capability_id",
    "execution_mode",
    "operator_approval_id",
    "receipt_status",
    "payload_sha256",
]

DEFAULT_PRIORITY_SITE_PACKS = [
    {
        "site_pack_id": "msn_article_comments",
        "display_name": "MSN article and comments",
        "adapter_id": "msn_article_comments",
        "source_kind": "web_article_with_comments",
        "domain_patterns": ["msn.com", "www.msn.com"],
        "capture_surface_ids": ["article_dom", "social-comment-wc_shadow_comments", "screenshot", "metadata_json"],
        "artifact_roles": ["article_html_or_text", "comments_json_or_text", "dom_snapshot", "screenshot", "metadata_json", "archive_receipt_json"],
        "fixture_types": ["saved_article_html_or_text", "saved_comments_json_or_text", "expected_content_extraction_json", "expected_comments_extraction_json", "expected_archive_receipt_json"],
        "notes": ["Covers the known MSN article plus shadow-root comments path through the shared pipeline."],
    },
    {
        "site_pack_id": "x_social_thread",
        "display_name": "X/Twitter post or thread",
        "adapter_id": "x_social_thread",
        "source_kind": "social_media_thread",
        "domain_patterns": ["x.com", "twitter.com"],
        "capture_surface_ids": ["post_text", "thread_replies", "screenshot", "metadata_json", "archive_receipt_json"],
        "artifact_roles": ["post_html_or_text", "thread_json_or_text", "screenshot", "metadata_json", "archive_receipt_json"],
        "fixture_types": ["saved_post_html_or_text", "saved_thread_json_or_text", "expected_comment_extraction_json", "expected_release_archive_json"],
        "notes": ["Covers social post, replies, screenshots, and archive receipts as fixture pack inputs."],
    },
    {
        "site_pack_id": "youtube_media_transcript",
        "display_name": "YouTube media transcript / ASR source",
        "adapter_id": "youtube_media_transcript",
        "source_kind": "media_or_transcript",
        "domain_patterns": ["youtube.com", "youtu.be"],
        "capture_surface_ids": ["media_metadata", "transcript_text_or_json", "screenshot", "source_url_metadata"],
        "artifact_roles": ["media_metadata_json", "transcript_text_or_json", "screenshot", "source_url_metadata", "archive_receipt_json"],
        "fixture_types": ["saved_transcript_text_or_json", "expected_total_export_package_json", "expected_evidence_queue_json", "expected_release_archive_json"],
        "notes": ["Keeps transcript/ASR output as a source-evidence adapter family rather than a site-specific duplicate pipeline."],
    },
    {
        "site_pack_id": "generic_news_article",
        "display_name": "Generic article / news page",
        "adapter_id": "generic_news_article",
        "source_kind": "web_article",
        "domain_patterns": ["operator_named_news_domain"],
        "capture_surface_ids": ["article_dom_or_text", "screenshot", "metadata_json", "archive_receipt_json"],
        "artifact_roles": ["article_html_or_text", "metadata_json", "screenshot", "archive_receipt_json"],
        "fixture_types": ["saved_article_html_or_text", "expected_content_extraction_json", "expected_total_export_package_json", "expected_archive_receipt_json"],
        "notes": ["Generic news site family used for named operator-selected article sources."],
    },
    {
        "site_pack_id": "comments_thread",
        "display_name": "Comments / replies thread",
        "adapter_id": "comments_thread",
        "source_kind": "comments",
        "domain_patterns": ["operator_named_comments_surface"],
        "capture_surface_ids": ["comments_json_or_text", "dom_snapshot", "screenshot", "metadata_json"],
        "artifact_roles": ["comments_json_or_text", "dom_snapshot", "screenshot", "metadata_json", "archive_receipt_json"],
        "fixture_types": ["saved_comments_json_or_text", "expected_comments_extraction_json", "expected_capture_bundle_json", "expected_release_archive_json"],
        "notes": ["Generic comment/reply thread fixture family for source sites with comment surfaces."],
    },
    {
        "site_pack_id": "archive_provider_receipt",
        "display_name": "Archive provider receipt",
        "adapter_id": "archive_provider_receipt",
        "source_kind": "archive_provider",
        "domain_patterns": ["archive_provider_output"],
        "capture_surface_ids": ["archive_receipt_json", "archived_url_metadata", "provider_status_json"],
        "artifact_roles": ["archive_receipt_json", "archived_url_metadata", "provider_status_json"],
        "fixture_types": ["archive_provider_receipt_json", "expected_archive_result_intake_json", "expected_archive_review_json"],
        "notes": ["Exercises provider receipt intake and archive review without binding to one provider implementation."],
    },
    {
        "site_pack_id": "gov_register_page",
        "display_name": "Government/register page",
        "adapter_id": "gov_register_page",
        "source_kind": "structured_register_page",
        "domain_patterns": ["gov.uk", "register-of-charities.charitycommission.gov.uk"],
        "capture_surface_ids": ["structured_page_text", "table_text", "metadata_json", "screenshot", "archive_receipt_json"],
        "artifact_roles": ["structured_page_text", "table_text", "metadata_json", "screenshot", "archive_receipt_json"],
        "fixture_types": ["saved_structured_page_text", "expected_table_extraction_json", "expected_total_export_package_json", "expected_archive_receipt_json"],
        "notes": ["Covers government/register-style pages with table/text preservation requirements."],
    },
]


@dataclass(frozen=True)
class PrioritySitePackExecutionCloseout:
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


def _normalise_pack(raw_pack: Mapping[str, Any], index: int, capability_ids: Sequence[str]) -> dict[str, Any]:
    pack = dict(raw_pack)
    site_pack_id = str(pack.get("site_pack_id") or pack.get("adapter_id") or f"priority_site_pack_{index}").strip()
    if not site_pack_id:
        raise ValueError(f"priority site pack at index {index} is missing site_pack_id")
    adapter_id = str(pack.get("adapter_id") or site_pack_id).strip()
    source_kind = str(pack.get("source_kind") or "web_source").strip()
    display_name = str(pack.get("display_name") or site_pack_id.replace("_", " ").title()).strip()
    domain_patterns = _strings(pack.get("domain_patterns") or ["operator_named_domain"])
    capture_surface_ids = _strings(pack.get("capture_surface_ids") or ["operator_supplied_artifacts"])
    artifact_roles = _strings(pack.get("artifact_roles") or ["source_artifact_file_or_text", "metadata_json", "archive_receipt_json"])
    fixture_types = _strings((pack.get("fixture_types") or []) + BASE_REQUIRED_FIXTURE_TYPES)
    requested_capabilities = _strings(pack.get("capability_ids") or capability_ids)
    selected_capabilities = [capability for capability in capability_ids if capability in requested_capabilities]
    if not selected_capabilities:
        selected_capabilities = list(capability_ids)
    expected_pipeline_stages = _strings(pack.get("expected_pipeline_stages") or DEFAULT_PIPELINE_STAGES)
    notes = _strings(pack.get("notes") or [])
    row_seed = {
        "site_pack_id": site_pack_id,
        "adapter_id": adapter_id,
        "source_kind": source_kind,
        "domain_patterns": domain_patterns,
        "capability_ids": selected_capabilities,
        "fixture_types": fixture_types,
    }
    return {
        "schema_version": "source_adapter_priority_site_fixture_pack_row_v1",
        "row_index": index,
        "priority_site_pack_row_id": stable_id("source_adapter.priority_site_pack", row_seed),
        "priority_adapter_fixture_seed_id": stable_id("source_adapter.priority_fixture_seed", {"site_pack_id": site_pack_id, "fixture_types": fixture_types}),
        "site_pack_id": site_pack_id,
        "adapter_id": adapter_id,
        "display_name": display_name,
        "source_kind": source_kind,
        "domain_patterns": domain_patterns,
        "capture_surface_ids": capture_surface_ids,
        "artifact_roles": artifact_roles,
        "fixture_types": fixture_types,
        "capability_ids": selected_capabilities,
        "expected_pipeline_stages": expected_pipeline_stages,
        "fixture_pack_status": "READY_FOR_LOCAL_FIXTURE_AUTHORING",
        "manual_smoke_status": "READY_FOR_OPERATOR_APPROVED_NAMED_SITE_SMOKE",
        "site_specific_code_status": "ADAPTER_SPEC_AND_FIXTURE_MAPPING_FIRST",
        "notes": notes,
    }


def _extract_capability_ids(final_closeout_package: Mapping[str, Any]) -> list[str]:
    handoff = final_closeout_package.get("source_adapter_runtime_fixture_smoke_final_handoff") or {}
    capabilities = _strings(handoff.get("capability_ids") or [])
    if capabilities:
        return capabilities
    acceptance_index = final_closeout_package.get("source_adapter_runtime_final_acceptance_index") or {}
    capabilities = _strings(acceptance_index.get("capability_ids") or [])
    if capabilities:
        return capabilities
    dry_batch = final_closeout_package.get("source_adapter_runtime_dry_run_receipt_batch") or {}
    capabilities = _strings(dry_batch.get("capability_ids") or [])
    if capabilities:
        return capabilities
    return list(DEFAULT_CAPABILITY_IDS)


def _validate_input(final_closeout_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if final_closeout_package.get("schema_version") not in {
        "source_adapter_runtime_fixture_smoke_final_closeout_v1",
        SCHEMA_VERSION,
    }:
        issues.append({"issue_id": "unexpected_schema", "severity": "error", "message": "runtime fixture smoke final closeout schema was not recognised"})
    status = final_closeout_package.get("runtime_fixture_smoke_final_closeout_status") or final_closeout_package.get("priority_site_pack_execution_closeout_status")
    if status not in {EXPECTED_INPUT_STATUS, STATUS}:
        issues.append({"issue_id": "unexpected_status", "severity": "error", "message": "runtime fixture smoke final closeout status is not ready"})
    handoff = final_closeout_package.get("source_adapter_runtime_fixture_smoke_final_handoff") or {}
    if handoff and handoff.get("handoff_status") != EXPECTED_INPUT_HANDOFF_STATUS:
        issues.append({"issue_id": "handoff_not_ready", "severity": "error", "message": "runtime fixture smoke final handoff is not ready for priority site packs"})
    return issues


def _build_local_fixture_row(site_pack: Mapping[str, Any], index: int) -> dict[str, Any]:
    seed = {"site_pack_id": site_pack["site_pack_id"], "fixture_types": site_pack["fixture_types"], "index": index}
    return {
        "schema_version": "source_adapter_priority_site_local_fixture_run_row_v1",
        "row_index": index,
        "local_fixture_run_row_id": stable_id("source_adapter.local_fixture_run", seed),
        "priority_site_pack_row_id": site_pack["priority_site_pack_row_id"],
        "site_pack_id": site_pack["site_pack_id"],
        "adapter_id": site_pack["adapter_id"],
        "source_kind": site_pack["source_kind"],
        "fixture_types": list(site_pack["fixture_types"]),
        "artifact_roles": list(site_pack["artifact_roles"]),
        "capability_ids": list(site_pack["capability_ids"]),
        "expected_pipeline_stages": list(site_pack["expected_pipeline_stages"]),
        "execution_mode": "local_fixture",
        "fixture_authoring_status": "READY_FOR_OPERATOR_OR_TEST_FIXTURE_FILES",
        "fixture_execution_status": "READY_FOR_SHARED_PIPELINE_LOCAL_EXECUTION",
        "required_validation": [
            "fixture_files_present",
            "expected_json_present",
            "shared_pipeline_stage_outputs_present",
            "runtime_receipts_present_or_dry_run_recorded",
        ],
    }


def _build_manual_smoke_row(site_pack: Mapping[str, Any], capability_id: str, index: int) -> dict[str, Any]:
    seed = {"site_pack_id": site_pack["site_pack_id"], "capability_id": capability_id, "index": index}
    required_operator_inputs = [
        "operator_named_site_id",
        "source_url_or_artifact_refs",
        "operator_approval_id",
        "execution_profile",
    ]
    if capability_id == "credential_lookup":
        required_operator_inputs.extend(["credential_reference_id", "provider_id"])
    elif capability_id == "archive_submit":
        required_operator_inputs.extend(["archive_provider_id", "submit_profile", "artifact_refs"])
    expected_receipt_fields = list(BASE_RECEIPT_FIELDS)
    if capability_id == "credential_lookup":
        expected_receipt_fields.extend(["credential_reference_id", "provider_id", "redacted_reference_hash"])
    elif capability_id == "archive_submit":
        expected_receipt_fields.extend(["archive_provider_id", "archive_job_id", "archive_url", "submitted_artifacts"])
    else:
        expected_receipt_fields.extend(["provider_execution_adapter_id", "controller_route_id"])
    return {
        "schema_version": "source_adapter_priority_site_manual_smoke_row_v1",
        "row_index": index,
        "manual_smoke_row_id": stable_id("source_adapter.priority_site_manual_smoke", seed),
        "manual_smoke_scenario_id": stable_id("source_adapter.manual_smoke_scenario", seed),
        "operator_approval_id": stable_id("source_adapter.operator_approval", seed),
        "priority_site_pack_row_id": site_pack["priority_site_pack_row_id"],
        "site_pack_id": site_pack["site_pack_id"],
        "adapter_id": site_pack["adapter_id"],
        "display_name": site_pack["display_name"],
        "source_kind": site_pack["source_kind"],
        "capability_id": capability_id,
        "execution_mode": "operator_approved_manual_smoke",
        "required_operator_inputs": _strings(required_operator_inputs),
        "expected_receipt_fields": _strings(expected_receipt_fields),
        "operator_named_site_required": True,
        "receipt_capture_required": True,
        "manual_smoke_status": "READY_FOR_NAMED_SITE_INPUT_AND_APPROVAL",
    }


def _build_roadmap_closeout(site_pack_rows: Sequence[Mapping[str, Any]], manual_smoke_rows: Sequence[Mapping[str, Any]], capability_ids: Sequence[str]) -> dict[str, Any]:
    fixture_types = sorted({fixture_type for row in site_pack_rows for fixture_type in row.get("fixture_types", [])})
    source_kinds = sorted({str(row.get("source_kind")) for row in site_pack_rows})
    return {
        "schema_version": ROADMAP_CLOSEOUT_SCHEMA_VERSION,
        "roadmap_coverage_status": "SOURCE_ADAPTER_PRIORITY_SITE_PACKS_READY_FOR_EXECUTION",
        "closed_sections": [
            "shared_adapter_pipeline_end_to_end",
            "runtime_controller_provider_dispatch",
            "runtime_receipt_capture",
            "priority_site_fixture_pack_matrix",
            "priority_site_local_fixture_run_plan",
            "priority_site_manual_live_smoke_plan",
            "keys_accounts_reference_lookup_surface",
        ],
        "capability_count": len(capability_ids),
        "capability_ids": list(capability_ids),
        "priority_site_pack_count": len(site_pack_rows),
        "manual_smoke_row_count": len(manual_smoke_rows),
        "source_kinds": source_kinds,
        "fixture_type_count": len(fixture_types),
        "fixture_types": fixture_types,
        "keys_accounts_lookup_surface": "keys_accounts.ui.credential_reference_selector",
        "runtime_receipt_coverage_status": "RECEIPT_FIELDS_DEFINED_FOR_PRIORITY_SITE_PACK_SMOKE",
        "remaining_operator_actions": [
            "choose named URLs or local artifacts for each priority site pack",
            "author fixture files and expected JSON for each selected pack",
            "run local fixture execution before manual/live smoke",
            "capture provider receipts for operator-approved executions",
        ],
    }


def build_source_adapter_priority_site_pack_execution_closeout(
    runtime_fixture_smoke_final_closeout_package: Mapping[str, Any],
    *,
    priority_site_packs: Sequence[Mapping[str, Any]] | None = None,
    operator_id: str = "operator",
    closeout_notes: Sequence[str] | None = None,
) -> PrioritySitePackExecutionCloseout:
    final_package = as_mapping(runtime_fixture_smoke_final_closeout_package, "runtime_fixture_smoke_final_closeout_package")
    issues = _validate_input(final_package)
    capability_ids = _extract_capability_ids(final_package)
    if not capability_ids:
        issues.append({"issue_id": "missing_capabilities", "severity": "error", "message": "no runtime capabilities were available for priority site packs"})
    raw_site_packs = list(priority_site_packs or DEFAULT_PRIORITY_SITE_PACKS)
    if not raw_site_packs:
        issues.append({"issue_id": "missing_site_packs", "severity": "error", "message": "at least one priority site pack is required"})
    site_pack_rows = [_normalise_pack(as_mapping(pack, f"priority_site_packs[{index}]"), index, capability_ids) for index, pack in enumerate(raw_site_packs)]
    seen_ids: set[str] = set()
    for row in site_pack_rows:
        if row["site_pack_id"] in seen_ids:
            issues.append({"issue_id": "duplicate_site_pack", "severity": "error", "site_pack_id": row["site_pack_id"], "message": "duplicate site_pack_id"})
        seen_ids.add(row["site_pack_id"])
    local_fixture_rows = [_build_local_fixture_row(row, index) for index, row in enumerate(site_pack_rows)]
    manual_smoke_rows: list[dict[str, Any]] = []
    for site_row in site_pack_rows:
        smoke_capabilities = [cap for cap in site_row["capability_ids"] if cap in {"archive_submit", "credential_lookup", "url_fetch_load", "browser_launch"}]
        if not smoke_capabilities:
            smoke_capabilities = list(site_row["capability_ids"][:2])
        for capability_id in smoke_capabilities:
            manual_smoke_rows.append(_build_manual_smoke_row(site_row, capability_id, len(manual_smoke_rows)))
    site_pack_matrix = {
        "schema_version": SITE_PACK_MATRIX_SCHEMA_VERSION,
        "site_pack_matrix_status": "SOURCE_ADAPTER_PRIORITY_SITE_PACK_MATRIX_READY",
        "priority_site_pack_count": len(site_pack_rows),
        "capability_ids": capability_ids,
        "priority_site_pack_rows": site_pack_rows,
    }
    local_fixture_run_plan = {
        "schema_version": LOCAL_FIXTURE_RUN_PLAN_SCHEMA_VERSION,
        "local_fixture_run_plan_status": "SOURCE_ADAPTER_PRIORITY_SITE_LOCAL_FIXTURE_RUN_PLAN_READY",
        "priority_site_pack_count": len(site_pack_rows),
        "local_fixture_run_count": len(local_fixture_rows),
        "local_fixture_run_rows": local_fixture_rows,
    }
    manual_smoke_plan = {
        "schema_version": MANUAL_SMOKE_PLAN_SCHEMA_VERSION,
        "manual_smoke_plan_status": "SOURCE_ADAPTER_PRIORITY_SITE_MANUAL_SMOKE_PLAN_READY",
        "execution_mode": "operator_approved_manual_smoke",
        "manual_smoke_row_count": len(manual_smoke_rows),
        "manual_smoke_rows": manual_smoke_rows,
    }
    roadmap_closeout = _build_roadmap_closeout(site_pack_rows, manual_smoke_rows, capability_ids)
    package_seed = {
        "final_closeout_id": final_package.get("source_adapter_runtime_fixture_smoke_final_closeout_id"),
        "site_pack_ids": [row["site_pack_id"] for row in site_pack_rows],
        "capability_ids": capability_ids,
    }
    closeout_id = stable_id("source_adapter.priority_site_pack_execution_closeout", package_seed)
    handoff = {
        "schema_version": HANDOFF_SCHEMA_VERSION,
        "handoff_status": HANDOFF_STATUS if not issues else "SOURCE_ADAPTER_PRIORITY_SITE_PACK_EXECUTION_BLOCKED",
        "source_adapter_priority_site_pack_execution_closeout_id": closeout_id,
        "priority_site_pack_row_ids": [row["priority_site_pack_row_id"] for row in site_pack_rows],
        "local_fixture_run_row_ids": [row["local_fixture_run_row_id"] for row in local_fixture_rows],
        "manual_smoke_row_ids": [row["manual_smoke_row_id"] for row in manual_smoke_rows],
        "ready_for_local_fixture_authoring": not issues,
        "ready_for_local_fixture_execution": not issues,
        "ready_for_operator_approved_manual_smoke": not issues,
        "required_next_stage": "operator_named_priority_site_fixture_authoring_and_smoke_execution" if not issues else "priority_site_pack_input_repair",
    }
    operator_summary = {
        "schema_version": OPERATOR_SUMMARY_SCHEMA_VERSION,
        "status": STATUS if not issues else "SOURCE_ADAPTER_PRIORITY_SITE_PACK_EXECUTION_CLOSEOUT_BLOCKED",
        "priority_site_pack_count": len(site_pack_rows),
        "local_fixture_run_count": len(local_fixture_rows),
        "manual_smoke_row_count": len(manual_smoke_rows),
        "capability_count": len(capability_ids),
        "next_actions": [
            "Author named priority site fixture packs from the fixture matrix.",
            "Run local fixture execution before live/manual smoke.",
            "Use operator approvals for every manual/live smoke row.",
            "Keep KEYS/ACCOUNTS credential material referenced, redacted, and receipt-backed.",
        ],
    }
    package = {
        "schema_version": SCHEMA_VERSION,
        "priority_site_pack_execution_closeout_status": STATUS if not issues else "SOURCE_ADAPTER_PRIORITY_SITE_PACK_EXECUTION_CLOSEOUT_BLOCKED",
        "source_adapter_priority_site_pack_execution_closeout_id": closeout_id,
        "source_adapter_runtime_fixture_smoke_final_closeout_id": final_package.get("source_adapter_runtime_fixture_smoke_final_closeout_id"),
        "operator_id": str(operator_id),
        "capability_count": len(capability_ids),
        "priority_site_pack_count": len(site_pack_rows),
        "local_fixture_run_count": len(local_fixture_rows),
        "manual_smoke_row_count": len(manual_smoke_rows),
        "issue_count": len(issues),
        "issues": issues,
        "closeout_notes": _strings(closeout_notes or []),
        "implementation_logic": {
            "input_source": "source_adapter_runtime_fixture_smoke_final_closeout",
            "priority_site_fixture_pack_matrix_built": True,
            "local_fixture_execution_plan_built": True,
            "operator_approved_manual_smoke_plan_built": True,
            "keys_accounts_reference_surface_preserved": True,
            "site_specific_code_default": "adapter_spec_fixture_mapping_first",
            "multi_site_pack_batch_supported": True,
        },
        "source_adapter_priority_site_fixture_pack_matrix": site_pack_matrix,
        "source_adapter_priority_site_local_fixture_run_plan": local_fixture_run_plan,
        "source_adapter_priority_site_manual_smoke_plan": manual_smoke_plan,
        "source_adapter_priority_site_roadmap_closeout": roadmap_closeout,
        "source_adapter_priority_site_pack_execution_handoff": handoff,
        "operator_summary": operator_summary,
    }
    return PrioritySitePackExecutionCloseout(package)


def example_runtime_fixture_smoke_final_closeout_package() -> dict[str, Any]:
    return {
        "schema_version": "source_adapter_runtime_fixture_smoke_final_closeout_v1",
        "runtime_fixture_smoke_final_closeout_status": EXPECTED_INPUT_STATUS,
        "source_adapter_runtime_fixture_smoke_final_closeout_id": "source_adapter_runtime_fixture_smoke_final_closeout.example",
        "source_adapter_runtime_fixture_smoke_final_handoff": {
            "schema_version": "source_adapter_runtime_fixture_smoke_final_handoff_v1",
            "handoff_status": EXPECTED_INPUT_HANDOFF_STATUS,
            "capability_ids": list(DEFAULT_CAPABILITY_IDS),
            "ready_for_named_priority_site_fixture_authoring": True,
            "ready_for_operator_approved_manual_live_smoke": True,
            "ready_for_runtime_dispatch_receipt_capture": True,
            "required_next_stage": "operator_named_priority_sites_and_live_smoke_execution",
        },
        "source_adapter_runtime_final_acceptance_index": {
            "schema_version": "source_adapter_runtime_final_acceptance_index_v1",
            "final_acceptance_status": "SOURCE_ADAPTER_RUNTIME_LOCAL_FIXTURE_AND_SMOKE_PLAN_ACCEPTED",
            "capability_ids": list(DEFAULT_CAPABILITY_IDS),
            "capability_count": len(DEFAULT_CAPABILITY_IDS),
        },
    }


def example_priority_site_pack_execution_closeout_package() -> dict[str, Any]:
    return build_source_adapter_priority_site_pack_execution_closeout(
        example_runtime_fixture_smoke_final_closeout_package(),
        operator_id="example_operator",
    ).as_dict()


def main() -> None:
    package = example_priority_site_pack_execution_closeout_package()
    assert package["schema_version"] == SCHEMA_VERSION
    assert package["priority_site_pack_execution_closeout_status"] == STATUS
    assert package["priority_site_pack_count"] >= 7
    assert package["manual_smoke_row_count"] >= package["priority_site_pack_count"]
    assert package["source_adapter_priority_site_pack_execution_handoff"]["handoff_status"] == HANDOFF_STATUS
    assert package["source_adapter_priority_site_roadmap_closeout"]["keys_accounts_lookup_surface"] == "keys_accounts.ui.credential_reference_selector"
    print("Source Adapter Priority Site Pack Execution Closeout self-test passed.")


if __name__ == "__main__":
    main()
