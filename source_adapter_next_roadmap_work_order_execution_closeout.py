from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from source_adapter_next_roadmap_section_selection_closeout import (
    HANDOFF_STATUS as SECTION_HANDOFF_STATUS,
    STATUS as SECTION_SELECTION_STATUS,
    example_next_roadmap_section_selection_closeout_package,
)

SCHEMA_VERSION = "source_adapter_next_roadmap_work_order_execution_closeout_v1"
EXECUTION_INDEX_SCHEMA_VERSION = "source_adapter_next_roadmap_work_order_execution_index_v1"
GUI_MANIFEST_SCHEMA_VERSION = "source_adapter_runtime_gui_controller_hardening_manifest_v1"
PROVIDER_MANIFEST_SCHEMA_VERSION = "source_adapter_provider_execution_activation_manifest_v1"
PRIORITY_FIXTURE_MANIFEST_SCHEMA_VERSION = "source_adapter_priority_fixture_pack_authoring_manifest_v1"
LIVE_SMOKE_MANIFEST_SCHEMA_VERSION = "source_adapter_live_smoke_receipt_capture_manifest_v1"
REGRESSION_PROMOTION_SCHEMA_VERSION = "source_adapter_regular_regression_promotion_manifest_v1"
DOC_REFRESH_SCHEMA_VERSION = "source_adapter_documentation_handoff_refresh_manifest_v1"
HANDOFF_SCHEMA_VERSION = "source_adapter_next_roadmap_execution_ready_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_next_roadmap_work_order_execution_operator_summary_v1"

STATUS = "SOURCE_ADAPTER_NEXT_ROADMAP_WORK_ORDER_EXECUTION_CLOSEOUT_BUILT"
HANDOFF_STATUS = "SOURCE_ADAPTER_NEXT_ROADMAP_EXECUTION_ARTIFACTS_READY"
BLOCKED_STATUS = "SOURCE_ADAPTER_NEXT_ROADMAP_WORK_ORDER_EXECUTION_BLOCKED"

SECTION_OUTPUT_ROLES = {
    "runtime_gui_controller_hardening": [
        "runtime_route_manifest",
        "gui_surface_binding_manifest",
        "controller_dispatch_contract",
        "keys_accounts_selector_contract",
    ],
    "provider_execution_adapter_activation": [
        "provider_execution_registry",
        "archive_submit_adapter_contract",
        "credential_reference_lookup_contract",
        "provider_receipt_validation_rules",
    ],
    "priority_site_fixture_pack_authoring": [
        "article_fixture_pack_seed",
        "social_post_fixture_pack_seed",
        "comments_thread_fixture_pack_seed",
        "media_transcript_fixture_pack_seed",
        "archive_receipt_fixture_pack_seed",
    ],
    "operator_live_smoke_receipt_capture": [
        "named_site_smoke_execution_manifest",
        "operator_approval_ledger",
        "provider_receipt_capture_template",
        "redacted_credential_reference_receipt_template",
    ],
    "regular_regression_promotion": [
        "source_adapter_regression_command_group",
        "runtime_cli_regression_tail",
        "fixture_pack_regression_tail",
        "session_manifest_export_state_tail",
    ],
    "documentation_handoff_refresh": [
        "source_adapter_closeout_summary",
        "codex_mega_prompt_handoff",
        "operator_runbook_refresh",
        "roadmap_audit_refresh_notes",
    ],
}

GUI_ROUTE_ROWS = [
    {
        "route_id": "source_adapter.gui.runtime.action_palette",
        "surface_id": "source_adapter.ui.runtime_action_palette",
        "controller_entrypoint": "source_adapter.controller.runtime.dispatch_selected_action",
        "required_inputs": ["adapter_id", "capability_id", "execution_mode", "operator_approval_id"],
        "receipt_role": "runtime_action_dispatch_receipt",
    },
    {
        "route_id": "source_adapter.gui.priority_fixture_pack_runner",
        "surface_id": "source_adapter.ui.priority_fixture_pack_runner",
        "controller_entrypoint": "source_adapter.controller.fixture_pack.run_local_matrix",
        "required_inputs": ["fixture_pack_id", "adapter_id", "artifact_refs"],
        "receipt_role": "fixture_pack_execution_receipt",
    },
    {
        "route_id": "source_adapter.gui.live_smoke_receipt_capture",
        "surface_id": "source_adapter.ui.operator_live_smoke_receipt_capture",
        "controller_entrypoint": "source_adapter.controller.live_smoke.capture_provider_receipt",
        "required_inputs": ["named_site_id", "operator_approval_id", "provider_receipt_ref"],
        "receipt_role": "operator_live_smoke_receipt",
    },
    {
        "route_id": "keys_accounts.gui.credential_reference_selector",
        "surface_id": "keys_accounts.ui.credential_reference_selector",
        "controller_entrypoint": "keys_accounts.controller.runtime.select_credential_reference",
        "required_inputs": ["provider_id", "credential_reference_id", "purpose"],
        "receipt_role": "redacted_credential_reference_receipt",
        "sidebar_label": "KEYS/ACCOUNTS",
    },
]

PROVIDER_ROWS = [
    {
        "provider_execution_adapter_id": "source_adapter.provider.archive_submit",
        "capability_id": "archive_submit",
        "execution_modes": ["dry_run", "operator_approved_manual_smoke"],
        "expected_receipt_fields": ["archive_provider_id", "archive_job_id", "archive_url", "submission_status", "submitted_artifacts"],
        "credential_surface": "keys_accounts.ui.credential_reference_selector",
    },
    {
        "provider_execution_adapter_id": "source_adapter.provider.release_upload",
        "capability_id": "release_upload",
        "execution_modes": ["dry_run", "operator_approved_manual_smoke"],
        "expected_receipt_fields": ["release_package_id", "upload_target_id", "upload_status", "artifact_refs", "receipt_sha256"],
        "credential_surface": "keys_accounts.ui.credential_reference_selector",
    },
    {
        "provider_execution_adapter_id": "source_adapter.provider.file_library_publish",
        "capability_id": "file_library_publish",
        "execution_modes": ["dry_run", "operator_approved_manual_smoke"],
        "expected_receipt_fields": ["library_path", "published_file_count", "publish_status", "receipt_sha256"],
        "credential_surface": "keys_accounts.ui.credential_reference_selector",
    },
    {
        "provider_execution_adapter_id": "keys_accounts.provider.credential_reference_lookup",
        "capability_id": "credential_lookup",
        "execution_modes": ["dry_run", "operator_approved_manual_smoke"],
        "expected_receipt_fields": ["credential_reference_id", "provider_id", "lookup_status", "redacted_reference_hash"],
        "credential_surface": "keys_accounts.ui.credential_reference_selector",
    },
]

PRIORITY_FIXTURE_PACK_ROWS = [
    {"fixture_pack_id": "source_adapter.fixture_pack.article_news", "adapter_id": "article", "source_kind": "web_article", "required_artifact_roles": ["article_html_or_text", "metadata_json", "screenshot", "archive_receipt_json"]},
    {"fixture_pack_id": "source_adapter.fixture_pack.social_post_thread", "adapter_id": "social_post", "source_kind": "social_media", "required_artifact_roles": ["post_html_or_text", "thread_json_or_text", "screenshot", "metadata_json", "archive_receipt_json"]},
    {"fixture_pack_id": "source_adapter.fixture_pack.comments_thread", "adapter_id": "comments_thread", "source_kind": "comments", "required_artifact_roles": ["comments_json_or_text", "dom_snapshot", "screenshot", "metadata_json"]},
    {"fixture_pack_id": "source_adapter.fixture_pack.media_transcript", "adapter_id": "media_transcript", "source_kind": "media_or_transcript", "required_artifact_roles": ["media_metadata_json", "transcript_text_or_json", "screenshot", "source_url_metadata"]},
    {"fixture_pack_id": "source_adapter.fixture_pack.archive_receipt", "adapter_id": "archive_receipt", "source_kind": "archive_provider", "required_artifact_roles": ["archive_receipt_json", "archived_url_metadata", "provider_status_json"]},
]

@dataclass(frozen=True)
class SourceAdapterNextRoadmapWorkOrderExecutionCloseout:
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


def _validate_input(selection_closeout: Mapping[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if selection_closeout.get("schema_version") != "source_adapter_next_roadmap_section_selection_closeout_v1":
        issues.append({"issue_id": "unexpected_schema", "severity": "error", "message": "next roadmap section selection closeout schema was not recognised"})
    if selection_closeout.get("next_roadmap_section_selection_closeout_status") != SECTION_SELECTION_STATUS:
        issues.append({"issue_id": "unexpected_status", "severity": "error", "message": "next roadmap section selection closeout is not built"})
    handoff = selection_closeout.get("source_adapter_next_roadmap_ready_handoff") or {}
    if handoff.get("handoff_status") != SECTION_HANDOFF_STATUS:
        issues.append({"issue_id": "handoff_not_ready", "severity": "error", "message": "next roadmap section handoff is not ready"})
    for flag in (
        "ready_for_next_largest_stable_patch",
        "ready_for_codex_mega_prompt_queue",
        "ready_for_regression_command_authoring",
        "ready_for_operator_gated_live_rows_when_selected",
    ):
        if handoff.get(flag) is not True:
            issues.append({"issue_id": f"{flag}_not_ready", "severity": "error", "message": f"handoff flag {flag} is not ready"})
    work_orders = selection_closeout.get("source_adapter_next_roadmap_work_order_manifest") or {}
    if not as_list(work_orders.get("work_order_rows"), "work_order_rows"):
        issues.append({"issue_id": "missing_work_order_rows", "severity": "error", "message": "no next roadmap work order rows were available"})
    return issues


def _work_order_rows(selection_closeout: Mapping[str, Any]) -> list[dict[str, Any]]:
    manifest = selection_closeout.get("source_adapter_next_roadmap_work_order_manifest") or {}
    rows = []
    for row in as_list(manifest.get("work_order_rows"), "work_order_rows"):
        if isinstance(row, Mapping):
            rows.append(dict(row))
    return rows


def _build_execution_index(selection_closeout: Mapping[str, Any], operator_id: str, issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for index, work_order in enumerate(_work_order_rows(selection_closeout)):
        section_id = str(work_order.get("section_id") or "").strip()
        output_roles = SECTION_OUTPUT_ROLES.get(section_id, ["section_execution_receipt"])
        ready = work_order.get("work_order_status") == "READY_FOR_IMPLEMENTATION" and not issues
        seed = {"work_order": work_order.get("work_order_row_id"), "section": section_id, "index": index}
        rows.append({
            "schema_version": "source_adapter_next_roadmap_work_order_execution_row_v1",
            "row_index": index,
            "work_order_execution_row_id": stable_id("source_adapter.next_roadmap_work_order_execution", seed),
            "work_order_row_id": work_order.get("work_order_row_id"),
            "section_id": section_id,
            "display_name": work_order.get("display_name"),
            "operator_id": operator_id,
            "required_patch_mode": work_order.get("required_patch_mode", "largest_stable_mega_patch"),
            "operator_gate": work_order.get("operator_gate"),
            "output_roles": output_roles,
            "output_role_count": len(output_roles),
            "execution_status": "SOURCE_ADAPTER_NEXT_ROADMAP_WORK_ORDER_EXECUTED" if ready else "NEEDS_WORK_ORDER_REVIEW",
        })
    executed_count = sum(1 for row in rows if row["execution_status"] == "SOURCE_ADAPTER_NEXT_ROADMAP_WORK_ORDER_EXECUTED")
    return {
        "schema_version": EXECUTION_INDEX_SCHEMA_VERSION,
        "execution_index_status": "SOURCE_ADAPTER_NEXT_ROADMAP_WORK_ORDER_EXECUTION_INDEX_BUILT" if rows and executed_count == len(rows) else "SOURCE_ADAPTER_NEXT_ROADMAP_WORK_ORDER_EXECUTION_INDEX_NEEDS_REVIEW",
        "work_order_execution_count": len(rows),
        "executed_work_order_count": executed_count,
        "operator_id": operator_id,
        "execution_rows": rows,
    }


def _manifest_status(rows: Sequence[Mapping[str, Any]], ready_status: str, blocked_status: str, issues: Sequence[Mapping[str, Any]]) -> str:
    return ready_status if rows and not issues else blocked_status


def _build_gui_controller_manifest(execution_index: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = []
    for index, route in enumerate(GUI_ROUTE_ROWS):
        seed = {"route": route["route_id"], "index": index}
        row = dict(route)
        row.update({
            "schema_version": "source_adapter_runtime_gui_controller_route_row_v1",
            "row_index": index,
            "gui_controller_route_row_id": stable_id("source_adapter.gui_controller_route", seed),
            "route_status": "READY_FOR_CONTROLLER_REGISTRATION" if not issues else "NEEDS_HANDOFF_REVIEW",
        })
        rows.append(row)
    return {
        "schema_version": GUI_MANIFEST_SCHEMA_VERSION,
        "gui_controller_hardening_status": _manifest_status(rows, "SOURCE_ADAPTER_RUNTIME_GUI_CONTROLLER_HARDENING_READY", "SOURCE_ADAPTER_RUNTIME_GUI_CONTROLLER_HARDENING_NEEDS_REVIEW", issues),
        "route_count": len(rows),
        "keys_accounts_label": "KEYS/ACCOUNTS",
        "execution_index_id": execution_index.get("work_order_execution_count"),
        "route_rows": rows,
    }


def _build_provider_manifest(issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = []
    for index, provider in enumerate(PROVIDER_ROWS):
        row = dict(provider)
        row.update({
            "schema_version": "source_adapter_provider_execution_activation_row_v1",
            "row_index": index,
            "provider_activation_row_id": stable_id("source_adapter.provider_activation", {"provider": provider["provider_execution_adapter_id"], "index": index}),
            "activation_status": "READY_FOR_DRY_RUN_AND_OPERATOR_APPROVED_EXECUTION" if not issues else "NEEDS_HANDOFF_REVIEW",
            "receipt_capture_required": True,
        })
        rows.append(row)
    return {
        "schema_version": PROVIDER_MANIFEST_SCHEMA_VERSION,
        "provider_execution_activation_status": _manifest_status(rows, "SOURCE_ADAPTER_PROVIDER_EXECUTION_ACTIVATION_READY", "SOURCE_ADAPTER_PROVIDER_EXECUTION_ACTIVATION_NEEDS_REVIEW", issues),
        "provider_activation_count": len(rows),
        "provider_activation_rows": rows,
    }


def _build_priority_fixture_manifest(issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = []
    for index, fixture in enumerate(PRIORITY_FIXTURE_PACK_ROWS):
        row = dict(fixture)
        row.update({
            "schema_version": "source_adapter_priority_fixture_pack_authoring_row_v1",
            "row_index": index,
            "fixture_pack_authoring_row_id": stable_id("source_adapter.priority_fixture_pack_authoring", {"fixture": fixture["fixture_pack_id"], "index": index}),
            "expected_pipeline_outputs": ["artifact_collection", "extraction", "capture_bundle", "total_export_package", "evidence_queue", "release_archive_closeout"],
            "authoring_status": "READY_FOR_LOCAL_FIXTURE_PACK_AUTHORING" if not issues else "NEEDS_HANDOFF_REVIEW",
        })
        rows.append(row)
    return {
        "schema_version": PRIORITY_FIXTURE_MANIFEST_SCHEMA_VERSION,
        "priority_fixture_pack_authoring_status": _manifest_status(rows, "SOURCE_ADAPTER_PRIORITY_FIXTURE_PACK_AUTHORING_READY", "SOURCE_ADAPTER_PRIORITY_FIXTURE_PACK_AUTHORING_NEEDS_REVIEW", issues),
        "fixture_pack_count": len(rows),
        "fixture_pack_rows": rows,
    }


def _build_live_smoke_manifest(provider_manifest: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    provider_rows = [dict(row) for row in as_list(provider_manifest.get("provider_activation_rows"), "provider_activation_rows") if isinstance(row, Mapping)]
    rows = []
    for index, provider in enumerate(provider_rows):
        requires_named_site = provider.get("capability_id") in {"archive_submit", "release_upload", "file_library_publish"}
        rows.append({
            "schema_version": "source_adapter_live_smoke_receipt_capture_row_v1",
            "row_index": index,
            "live_smoke_receipt_capture_row_id": stable_id("source_adapter.live_smoke_receipt_capture", {"provider": provider.get("provider_execution_adapter_id"), "index": index}),
            "provider_execution_adapter_id": provider.get("provider_execution_adapter_id"),
            "capability_id": provider.get("capability_id"),
            "operator_named_site_required": requires_named_site,
            "operator_approval_id_required": True,
            "expected_receipt_fields": list(provider.get("expected_receipt_fields") or []),
            "credential_surface": provider.get("credential_surface"),
            "capture_status": "READY_FOR_OPERATOR_APPROVED_RECEIPT_CAPTURE" if not issues else "NEEDS_HANDOFF_REVIEW",
        })
    return {
        "schema_version": LIVE_SMOKE_MANIFEST_SCHEMA_VERSION,
        "live_smoke_receipt_capture_status": _manifest_status(rows, "SOURCE_ADAPTER_LIVE_SMOKE_RECEIPT_CAPTURE_READY", "SOURCE_ADAPTER_LIVE_SMOKE_RECEIPT_CAPTURE_NEEDS_REVIEW", issues),
        "live_smoke_receipt_capture_count": len(rows),
        "live_smoke_receipt_capture_rows": rows,
    }


def _build_regression_manifest(selection_closeout: Mapping[str, Any], execution_index: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    prior = selection_closeout.get("source_adapter_next_roadmap_regression_command_manifest") or {}
    prior_rows = [dict(row) for row in as_list(prior.get("command_rows"), "command_rows") if isinstance(row, Mapping)]
    execution_rows = [dict(row) for row in as_list(execution_index.get("execution_rows"), "execution_rows") if isinstance(row, Mapping)]
    rows = []
    for index, row in enumerate(execution_rows):
        command_group = next((cmd.get("command_group") for cmd in prior_rows if cmd.get("section_id") == row.get("section_id")), row.get("section_id"))
        rows.append({
            "schema_version": "source_adapter_regular_regression_promotion_row_v1",
            "row_index": index,
            "regression_promotion_row_id": stable_id("source_adapter.regression_promotion", {"section": row.get("section_id"), "index": index}),
            "section_id": row.get("section_id"),
            "command_group": command_group,
            "safe_execution_mode": "local_fixture_or_dry_run_regression",
            "includes_git_diff_check": True,
            "compile_asr_tools_test_only": True,
            "promotion_status": "READY_FOR_REGULAR_REGRESSION_PROMOTION" if not issues else "NEEDS_HANDOFF_REVIEW",
        })
    return {
        "schema_version": REGRESSION_PROMOTION_SCHEMA_VERSION,
        "regular_regression_promotion_status": _manifest_status(rows, "SOURCE_ADAPTER_REGULAR_REGRESSION_PROMOTION_READY", "SOURCE_ADAPTER_REGULAR_REGRESSION_PROMOTION_NEEDS_REVIEW", issues),
        "regression_promotion_count": len(rows),
        "regression_promotion_rows": rows,
    }


def _build_doc_refresh_manifest(execution_index: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    doc_rows = [
        {"doc_role": "roadmap_audit_update", "target_files": ["SOURCE_EVIDENCE_ROADMAP_COVERAGE_AUDIT.md", "SOURCE_EVIDENCE_ROADMAP.md"]},
        {"doc_role": "current_state_handoff_update", "target_files": ["CURRENT_DEV_STATE.md", "PROJECT_CURRENT_STATE_HANDOFF.md"]},
        {"doc_role": "operator_runtime_runbook_update", "target_files": ["SOURCE_ADAPTER_RUNTIME_OPERATOR_RUNBOOK.md"]},
        {"doc_role": "codex_mega_prompt_queue_update", "target_files": ["SOURCE_ADAPTER_NEXT_ROADMAP_CODEX_QUEUE.md"]},
    ]
    rows = []
    for index, row in enumerate(doc_rows):
        rows.append({
            "schema_version": "source_adapter_documentation_handoff_refresh_row_v1",
            "row_index": index,
            "documentation_refresh_row_id": stable_id("source_adapter.documentation_refresh", {"role": row["doc_role"], "index": index}),
            "doc_role": row["doc_role"],
            "target_files": row["target_files"],
            "references_work_order_execution_count": execution_index.get("work_order_execution_count", 0),
            "refresh_status": "READY_FOR_DOCUMENTATION_HANDOFF_REFRESH" if not issues else "NEEDS_HANDOFF_REVIEW",
        })
    return {
        "schema_version": DOC_REFRESH_SCHEMA_VERSION,
        "documentation_handoff_refresh_status": _manifest_status(rows, "SOURCE_ADAPTER_DOCUMENTATION_HANDOFF_REFRESH_READY", "SOURCE_ADAPTER_DOCUMENTATION_HANDOFF_REFRESH_NEEDS_REVIEW", issues),
        "documentation_refresh_count": len(rows),
        "documentation_refresh_rows": rows,
        "keys_accounts_label": "KEYS/ACCOUNTS",
    }


def _build_handoff(closeout_id: str, execution_index: Mapping[str, Any], gui_manifest: Mapping[str, Any], provider_manifest: Mapping[str, Any], fixture_manifest: Mapping[str, Any], live_smoke_manifest: Mapping[str, Any], regression_manifest: Mapping[str, Any], doc_manifest: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ready = (
        not issues
        and execution_index.get("execution_index_status") == "SOURCE_ADAPTER_NEXT_ROADMAP_WORK_ORDER_EXECUTION_INDEX_BUILT"
        and gui_manifest.get("gui_controller_hardening_status") == "SOURCE_ADAPTER_RUNTIME_GUI_CONTROLLER_HARDENING_READY"
        and provider_manifest.get("provider_execution_activation_status") == "SOURCE_ADAPTER_PROVIDER_EXECUTION_ACTIVATION_READY"
        and fixture_manifest.get("priority_fixture_pack_authoring_status") == "SOURCE_ADAPTER_PRIORITY_FIXTURE_PACK_AUTHORING_READY"
        and live_smoke_manifest.get("live_smoke_receipt_capture_status") == "SOURCE_ADAPTER_LIVE_SMOKE_RECEIPT_CAPTURE_READY"
        and regression_manifest.get("regular_regression_promotion_status") == "SOURCE_ADAPTER_REGULAR_REGRESSION_PROMOTION_READY"
        and doc_manifest.get("documentation_handoff_refresh_status") == "SOURCE_ADAPTER_DOCUMENTATION_HANDOFF_REFRESH_READY"
    )
    return {
        "schema_version": HANDOFF_SCHEMA_VERSION,
        "handoff_status": HANDOFF_STATUS if ready else BLOCKED_STATUS,
        "source_adapter_next_roadmap_work_order_execution_closeout_id": closeout_id,
        "ready_for_gui_controller_implementation_patch": ready,
        "ready_for_provider_execution_activation_patch": ready,
        "ready_for_priority_fixture_pack_authoring_patch": ready,
        "ready_for_operator_approved_live_smoke_receipt_capture": ready,
        "ready_for_regular_regression_promotion": ready,
        "ready_for_documentation_handoff_refresh": ready,
        "required_next_stage": "runtime_gui_provider_fixture_implementation" if ready else "next_roadmap_work_order_execution_review",
        "work_order_execution_count": execution_index.get("work_order_execution_count", 0),
        "provider_activation_count": provider_manifest.get("provider_activation_count", 0),
        "fixture_pack_count": fixture_manifest.get("fixture_pack_count", 0),
        "live_smoke_receipt_capture_count": live_smoke_manifest.get("live_smoke_receipt_capture_count", 0),
        "regression_promotion_count": regression_manifest.get("regression_promotion_count", 0),
    }


def build_source_adapter_next_roadmap_work_order_execution_closeout(
    next_roadmap_section_selection_closeout_package: Mapping[str, Any],
    *,
    operator_id: str = "operator",
    closeout_notes: Sequence[str] | None = None,
) -> SourceAdapterNextRoadmapWorkOrderExecutionCloseout:
    selection_closeout = as_mapping(next_roadmap_section_selection_closeout_package, "next_roadmap_section_selection_closeout_package")
    issues = _validate_input(selection_closeout)
    execution_index = _build_execution_index(selection_closeout, operator_id, issues)
    gui_manifest = _build_gui_controller_manifest(execution_index, issues)
    provider_manifest = _build_provider_manifest(issues)
    fixture_manifest = _build_priority_fixture_manifest(issues)
    live_smoke_manifest = _build_live_smoke_manifest(provider_manifest, issues)
    regression_manifest = _build_regression_manifest(selection_closeout, execution_index, issues)
    doc_manifest = _build_doc_refresh_manifest(execution_index, issues)
    seed = {
        "selection_closeout_id": selection_closeout.get("source_adapter_next_roadmap_section_selection_closeout_id"),
        "operator_id": operator_id,
        "work_order_execution_count": execution_index.get("work_order_execution_count"),
        "provider_activation_count": provider_manifest.get("provider_activation_count"),
    }
    closeout_id = stable_id("source_adapter.next_roadmap_work_order_execution_closeout", seed)
    handoff = _build_handoff(closeout_id, execution_index, gui_manifest, provider_manifest, fixture_manifest, live_smoke_manifest, regression_manifest, doc_manifest, issues)
    ready = handoff.get("handoff_status") == HANDOFF_STATUS
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": STATUS if ready else BLOCKED_STATUS,
        "work_order_execution_count": execution_index.get("work_order_execution_count", 0),
        "provider_activation_count": provider_manifest.get("provider_activation_count", 0),
        "fixture_pack_count": fixture_manifest.get("fixture_pack_count", 0),
        "live_smoke_receipt_capture_count": live_smoke_manifest.get("live_smoke_receipt_capture_count", 0),
        "regression_promotion_count": regression_manifest.get("regression_promotion_count", 0),
        "keys_accounts_label": "KEYS/ACCOUNTS",
        "next_actions": [
            "Implement GUI/controller route registration from the hardening manifest.",
            "Activate provider execution adapters with dry-run receipts first, then named operator-approved live rows.",
            "Author priority fixture packs and promote accepted rows into the regular regression tail.",
            "Refresh roadmap, current state, handoff, and operator runbook documents after implementation.",
        ],
    }
    package = {
        "schema_version": SCHEMA_VERSION,
        "next_roadmap_work_order_execution_closeout_status": STATUS if ready else BLOCKED_STATUS,
        "source_adapter_next_roadmap_work_order_execution_closeout_id": closeout_id,
        "source_adapter_next_roadmap_section_selection_closeout_id": selection_closeout.get("source_adapter_next_roadmap_section_selection_closeout_id"),
        "operator_id": str(operator_id),
        "issue_count": len(issues),
        "issues": list(issues),
        "closeout_notes": _strings(closeout_notes or []),
        "implementation_logic": {
            "input_source": "source_adapter_next_roadmap_section_selection_closeout",
            "work_order_execution_index_built": True,
            "gui_controller_manifest_built": True,
            "provider_execution_activation_manifest_built": True,
            "priority_fixture_pack_authoring_manifest_built": True,
            "live_smoke_receipt_capture_manifest_built": True,
            "regular_regression_promotion_manifest_built": True,
            "documentation_handoff_refresh_manifest_built": True,
            "keys_accounts_label_preserved": True,
            "largest_stable_patch_mode_preserved": True,
        },
        "source_adapter_next_roadmap_work_order_execution_index": execution_index,
        "source_adapter_runtime_gui_controller_hardening_manifest": gui_manifest,
        "source_adapter_provider_execution_activation_manifest": provider_manifest,
        "source_adapter_priority_fixture_pack_authoring_manifest": fixture_manifest,
        "source_adapter_live_smoke_receipt_capture_manifest": live_smoke_manifest,
        "source_adapter_regular_regression_promotion_manifest": regression_manifest,
        "source_adapter_documentation_handoff_refresh_manifest": doc_manifest,
        "source_adapter_next_roadmap_execution_ready_handoff": handoff,
        "operator_summary": operator_summary,
    }
    return SourceAdapterNextRoadmapWorkOrderExecutionCloseout(package)


def example_next_roadmap_work_order_execution_closeout_package() -> dict[str, Any]:
    return build_source_adapter_next_roadmap_work_order_execution_closeout(
        example_next_roadmap_section_selection_closeout_package(),
        operator_id="example_operator",
    ).as_dict()


def main() -> None:
    package = example_next_roadmap_work_order_execution_closeout_package()
    assert package["schema_version"] == SCHEMA_VERSION
    assert package["next_roadmap_work_order_execution_closeout_status"] == STATUS
    assert package["source_adapter_next_roadmap_execution_ready_handoff"]["handoff_status"] == HANDOFF_STATUS
    assert package["operator_summary"]["keys_accounts_label"] == "KEYS/ACCOUNTS"
    assert package["source_adapter_provider_execution_activation_manifest"]["provider_activation_count"] >= 4
    print("Source Adapter Next Roadmap Work Order Execution Closeout self-test passed.")


if __name__ == "__main__":
    main()
