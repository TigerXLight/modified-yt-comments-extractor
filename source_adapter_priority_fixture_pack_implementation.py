from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from source_adapter_runtime_gui_provider_implementation import (
    HANDOFF_STATUS as RUNTIME_GUI_HANDOFF_STATUS,
    SCHEMA_VERSION as RUNTIME_GUI_SCHEMA_VERSION,
    STATUS as RUNTIME_GUI_STATUS,
    RuntimeControllerRegistry,
    _payload_for_provider,
    example_runtime_gui_provider_implementation_package,
)

SCHEMA_VERSION = "source_adapter_priority_fixture_pack_implementation_v1"
CATALOG_SCHEMA_VERSION = "source_adapter_priority_fixture_pack_catalog_v1"
EXECUTION_MATRIX_SCHEMA_VERSION = "source_adapter_priority_fixture_pack_execution_matrix_v1"
DISPATCH_RECEIPT_SCHEMA_VERSION = "source_adapter_priority_fixture_pack_dispatch_receipt_batch_v1"
GUI_INSTALLATION_SCHEMA_VERSION = "source_adapter_priority_fixture_pack_gui_installation_checklist_v1"
NAMED_SITE_SMOKE_SCHEMA_VERSION = "source_adapter_priority_fixture_pack_named_site_smoke_queue_v1"
HANDOFF_SCHEMA_VERSION = "source_adapter_priority_fixture_pack_implementation_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_priority_fixture_pack_implementation_operator_summary_v1"

STATUS = "SOURCE_ADAPTER_PRIORITY_FIXTURE_PACK_IMPLEMENTATION_BUILT"
HANDOFF_STATUS = "SOURCE_ADAPTER_PRIORITY_FIXTURE_PACK_IMPLEMENTATION_READY_FOR_OPERATOR_LIVE_SMOKE_EXECUTION"
BLOCKED_STATUS = "SOURCE_ADAPTER_PRIORITY_FIXTURE_PACK_IMPLEMENTATION_NEEDS_REVIEW"
DRY_RUN_MODE = "dry_run"
OPERATOR_APPROVED_MODE = "operator_approved_manual_smoke"
KEYS_ACCOUNTS_SURFACE = "keys_accounts.ui.credential_reference_selector"


@dataclass(frozen=True)
class SourceAdapterPriorityFixturePackImplementation:
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


def _rows(container: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    return [dict(row) for row in as_list(container.get(key), key) if isinstance(row, Mapping)]


def _validate_runtime_gui_package(runtime_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if runtime_package.get("schema_version") != RUNTIME_GUI_SCHEMA_VERSION:
        issues.append({"issue_id": "unexpected_schema", "severity": "error", "message": "runtime GUI provider implementation schema was not recognised"})
    if runtime_package.get("runtime_gui_provider_implementation_status") != RUNTIME_GUI_STATUS:
        issues.append({"issue_id": "unexpected_status", "severity": "error", "message": "runtime GUI provider implementation status is not built"})
    if int(runtime_package.get("issue_count", 0) or 0) != 0:
        issues.append({"issue_id": "upstream_issues_present", "severity": "error", "message": "runtime GUI provider implementation contains upstream issues"})
    handoff = runtime_package.get("source_adapter_runtime_gui_provider_implementation_handoff") or {}
    if not isinstance(handoff, Mapping) or handoff.get("handoff_status") != RUNTIME_GUI_HANDOFF_STATUS:
        issues.append({"issue_id": "handoff_not_ready", "severity": "error", "message": "runtime GUI provider implementation handoff is not ready"})
    route_registry = runtime_package.get("source_adapter_runtime_gui_controller_route_registry") or {}
    provider_registry = runtime_package.get("source_adapter_runtime_provider_execution_registry") or {}
    credential_selector = runtime_package.get("source_adapter_keys_accounts_credential_reference_selector") or {}
    if not isinstance(route_registry, Mapping) or not _rows(route_registry, "route_rows"):
        issues.append({"issue_id": "route_registry_missing", "severity": "error", "message": "runtime route registry is missing"})
    if not isinstance(provider_registry, Mapping) or not _rows(provider_registry, "provider_rows"):
        issues.append({"issue_id": "provider_registry_missing", "severity": "error", "message": "runtime provider registry is missing"})
    if not isinstance(credential_selector, Mapping) or credential_selector.get("sidebar_label") != "KEYS/ACCOUNTS":
        issues.append({"issue_id": "keys_accounts_selector_not_ready", "severity": "error", "message": "KEYS/ACCOUNTS selector was not preserved"})
    return issues


PRIORITY_FIXTURE_PACK_TEMPLATES: tuple[dict[str, Any], ...] = (
    {
        "adapter_id": "article",
        "source_kind": "web_article",
        "display_name": "Article / news page",
        "fixture_family": "article_news_page",
        "local_fixture_dir": "fixtures/source_adapter_priority/article_news_page",
        "artifact_roles": ["article_html_or_text", "metadata_json", "screenshot", "archive_receipt_json"],
        "fixture_files": ["source.html", "metadata.json", "expected_extraction.json", "expected_total_export.json", "archive_receipt.json"],
        "expected_pipeline_outputs": ["artifact_collection", "content_extraction", "capture_bundle", "total_export_package", "evidence_queue", "release_archive_closeout"],
    },
    {
        "adapter_id": "social_post",
        "source_kind": "social_media",
        "display_name": "Social post / thread",
        "fixture_family": "social_post_thread",
        "local_fixture_dir": "fixtures/source_adapter_priority/social_post_thread",
        "artifact_roles": ["post_html_or_text", "thread_json_or_text", "screenshot", "metadata_json", "archive_receipt_json"],
        "fixture_files": ["post.html", "thread.json", "metadata.json", "expected_comment_extraction.json", "expected_release_archive.json"],
        "expected_pipeline_outputs": ["artifact_collection", "comment_extraction", "capture_bundle", "total_export_package", "evidence_queue", "release_archive_closeout"],
    },
    {
        "adapter_id": "comments_thread",
        "source_kind": "comments",
        "display_name": "Comments / replies thread",
        "fixture_family": "comments_replies_thread",
        "local_fixture_dir": "fixtures/source_adapter_priority/comments_replies_thread",
        "artifact_roles": ["comments_json_or_text", "dom_snapshot", "screenshot", "metadata_json"],
        "fixture_files": ["comments.json", "dom_snapshot.html", "metadata.json", "expected_comments_extraction.json", "expected_capture_bundle.json"],
        "expected_pipeline_outputs": ["artifact_collection", "comment_extraction", "capture_bundle", "total_export_package", "evidence_queue", "release_archive_closeout"],
    },
    {
        "adapter_id": "media_transcript",
        "source_kind": "media_or_transcript",
        "display_name": "Media transcript / ASR source",
        "fixture_family": "media_transcript_asr_source",
        "local_fixture_dir": "fixtures/source_adapter_priority/media_transcript_asr_source",
        "artifact_roles": ["media_metadata_json", "transcript_text_or_json", "screenshot", "source_url_metadata"],
        "fixture_files": ["media_metadata.json", "transcript.txt", "source_url_metadata.json", "expected_total_export.json", "expected_evidence_queue.json"],
        "expected_pipeline_outputs": ["artifact_collection", "transcript_extraction", "capture_bundle", "total_export_package", "evidence_queue", "release_archive_closeout"],
    },
    {
        "adapter_id": "archive_receipt",
        "source_kind": "archive_provider",
        "display_name": "Archive provider receipt",
        "fixture_family": "archive_provider_receipt",
        "local_fixture_dir": "fixtures/source_adapter_priority/archive_provider_receipt",
        "artifact_roles": ["archive_receipt_json", "archived_url_metadata", "provider_status_json"],
        "fixture_files": ["archive_receipt.json", "archived_url_metadata.json", "provider_status.json", "expected_archive_result_intake.json", "expected_archive_review.json"],
        "expected_pipeline_outputs": ["artifact_collection", "archive_result_intake", "archive_review", "capture_bundle", "total_export_package", "release_archive_closeout"],
    },
)


def _route_rows(runtime_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    return _rows(runtime_package.get("source_adapter_runtime_gui_controller_route_registry") or {}, "route_rows")


def _provider_rows(runtime_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    return _rows(runtime_package.get("source_adapter_runtime_provider_execution_registry") or {}, "provider_rows")


def _route_id_for_provider(provider: Mapping[str, Any], routes: Sequence[Mapping[str, Any]], *, pack_runner: bool = False) -> str:
    provider_id = str(provider.get("provider_execution_adapter_id") or "")
    if provider_id == "keys_accounts.provider.credential_reference_lookup":
        preferred = "keys_accounts.gui.credential_reference_selector"
    elif pack_runner:
        preferred = "source_adapter.gui.priority_fixture_pack_runner"
    else:
        preferred = "source_adapter.gui.runtime.action_palette"
    route = next((row for row in routes if row.get("route_id") == preferred), None)
    if route:
        return str(route.get("route_id"))
    return str(routes[0].get("route_id")) if routes else ""


def _build_fixture_pack_catalog(runtime_package: Mapping[str, Any], issues: Sequence[Mapping[str, Any]], fixture_pack_notes: Sequence[str]) -> dict[str, Any]:
    route_ids = [str(row.get("route_id")) for row in _route_rows(runtime_package)]
    provider_ids = [str(row.get("provider_execution_adapter_id")) for row in _provider_rows(runtime_package)]
    rows: list[dict[str, Any]] = []
    for index, template in enumerate(PRIORITY_FIXTURE_PACK_TEMPLATES):
        pack_seed = {"adapter_id": template["adapter_id"], "source_kind": template["source_kind"], "index": index}
        rows.append({
            "schema_version": "source_adapter_priority_fixture_pack_catalog_row_v1",
            "row_index": index,
            "fixture_pack_id": stable_id("source_adapter.priority_fixture_pack", pack_seed),
            "adapter_id": template["adapter_id"],
            "source_kind": template["source_kind"],
            "display_name": template["display_name"],
            "fixture_family": template["fixture_family"],
            "local_fixture_dir": template["local_fixture_dir"],
            "fixture_files": list(template["fixture_files"]),
            "artifact_roles": list(template["artifact_roles"]),
            "expected_pipeline_outputs": list(template["expected_pipeline_outputs"]),
            "route_ids": route_ids,
            "provider_execution_adapter_ids": provider_ids,
            "keys_accounts_surface": KEYS_ACCOUNTS_SURFACE,
            "fixture_pack_status": "READY_FOR_LOCAL_FIXTURE_AUTHORING_AND_DISPATCH" if not issues else "NEEDS_RUNTIME_REVIEW",
        })
    return {
        "schema_version": CATALOG_SCHEMA_VERSION,
        "fixture_pack_catalog_status": "SOURCE_ADAPTER_PRIORITY_FIXTURE_PACK_CATALOG_READY" if rows and not issues else "SOURCE_ADAPTER_PRIORITY_FIXTURE_PACK_CATALOG_NEEDS_REVIEW",
        "fixture_pack_count": len(rows),
        "provider_count": len(provider_ids),
        "route_count": len(route_ids),
        "fixture_pack_notes": _strings(fixture_pack_notes),
        "fixture_pack_rows": rows,
    }


def _build_execution_matrix(catalog: Mapping[str, Any], runtime_package: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    routes = _route_rows(runtime_package)
    providers = _provider_rows(runtime_package)
    packs = _rows(catalog, "fixture_pack_rows")
    rows: list[dict[str, Any]] = []
    for pack_index, pack in enumerate(packs):
        for provider_index, provider in enumerate(providers):
            route_id = _route_id_for_provider(provider, routes, pack_runner=True)
            seed = {"fixture_pack_id": pack.get("fixture_pack_id"), "provider": provider.get("provider_execution_adapter_id"), "route": route_id}
            rows.append({
                "schema_version": "source_adapter_priority_fixture_pack_execution_matrix_row_v1",
                "row_index": len(rows),
                "fixture_pack_execution_row_id": stable_id("source_adapter.fixture_pack_execution", seed),
                "fixture_pack_id": pack.get("fixture_pack_id"),
                "adapter_id": pack.get("adapter_id"),
                "source_kind": pack.get("source_kind"),
                "fixture_family": pack.get("fixture_family"),
                "local_fixture_dir": pack.get("local_fixture_dir"),
                "provider_execution_adapter_id": provider.get("provider_execution_adapter_id"),
                "capability_id": provider.get("capability_id"),
                "controller_route_id": route_id,
                "expected_receipt_fields": _strings(provider.get("expected_receipt_fields") or []),
                "fixture_files": _strings(pack.get("fixture_files") or []),
                "artifact_roles": _strings(pack.get("artifact_roles") or []),
                "execution_mode": DRY_RUN_MODE,
                "operator_approval_id": stable_id("source_adapter.fixture_pack_operator_approval", {"pack": pack_index, "provider": provider_index}),
                "execution_status": "READY_FOR_LOCAL_FIXTURE_DISPATCH" if route_id and not issues else "NEEDS_ROUTE_OR_PROVIDER_REVIEW",
            })
    return {
        "schema_version": EXECUTION_MATRIX_SCHEMA_VERSION,
        "fixture_pack_execution_matrix_status": "SOURCE_ADAPTER_PRIORITY_FIXTURE_PACK_EXECUTION_MATRIX_READY" if rows and not issues else "SOURCE_ADAPTER_PRIORITY_FIXTURE_PACK_EXECUTION_MATRIX_NEEDS_REVIEW",
        "fixture_pack_execution_row_count": len(rows),
        "fixture_pack_count": len(packs),
        "provider_count": len(providers),
        "execution_rows": rows,
    }


def _provider_index(runtime_package: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row.get("provider_execution_adapter_id")): row for row in _provider_rows(runtime_package)}


def _payload_for_fixture_provider(provider: Mapping[str, Any], execution_row: Mapping[str, Any]) -> dict[str, Any]:
    payload = _payload_for_provider(provider)
    payload.update({
        "fixture_pack_id": execution_row.get("fixture_pack_id"),
        "adapter_id": execution_row.get("adapter_id"),
        "source_kind": execution_row.get("source_kind"),
        "fixture_family": execution_row.get("fixture_family"),
        "local_fixture_dir": execution_row.get("local_fixture_dir"),
    })
    if "credential_reference_id" in payload:
        payload["credential_reference_id"] = f"keys_accounts://fixture/{execution_row.get('adapter_id')}/{provider.get('capability_id')}"
    return payload


def _build_dispatch_receipts(execution_matrix: Mapping[str, Any], runtime_package: Mapping[str, Any], operator_id: str, issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    routes = _route_rows(runtime_package)
    providers = _provider_rows(runtime_package)
    provider_by_id = _provider_index(runtime_package)
    dispatcher = RuntimeControllerRegistry(routes, providers)
    rows: list[dict[str, Any]] = []
    if not issues:
        for index, execution_row in enumerate(_rows(execution_matrix, "execution_rows")):
            provider_id = str(execution_row.get("provider_execution_adapter_id") or "")
            provider = provider_by_id.get(provider_id, {})
            receipt = dispatcher.dispatch(
                route_id=str(execution_row.get("controller_route_id") or ""),
                provider_execution_adapter_id=provider_id,
                payload=_payload_for_fixture_provider(provider, execution_row),
                execution_mode=DRY_RUN_MODE,
                operator_approval_id=str(execution_row.get("operator_approval_id") or f"{operator_id}.fixture_pack.approval"),
            )
            receipt.update({
                "schema_version": "source_adapter_priority_fixture_pack_dispatch_receipt_row_v1",
                "row_index": index,
                "fixture_pack_dispatch_receipt_row_id": stable_id("source_adapter.fixture_pack_dispatch_receipt", {"receipt": receipt.get("runtime_dispatch_receipt_id"), "index": index}),
                "fixture_pack_execution_row_id": execution_row.get("fixture_pack_execution_row_id"),
                "fixture_pack_id": execution_row.get("fixture_pack_id"),
                "adapter_id": execution_row.get("adapter_id"),
                "source_kind": execution_row.get("source_kind"),
                "fixture_family": execution_row.get("fixture_family"),
                "local_fixture_dir": execution_row.get("local_fixture_dir"),
                "dispatch_acceptance_status": "ACCEPTED_FOR_PRIORITY_FIXTURE_PACK_REGRESSION" if not receipt.get("missing_receipt_fields") else "NEEDS_FIXTURE_RECEIPT_REVIEW",
            })
            rows.append(receipt)
    return {
        "schema_version": DISPATCH_RECEIPT_SCHEMA_VERSION,
        "fixture_pack_dispatch_receipt_batch_status": "SOURCE_ADAPTER_PRIORITY_FIXTURE_PACK_DISPATCH_RECEIPTS_ACCEPTED" if rows and len(rows) == int(execution_matrix.get("fixture_pack_execution_row_count", 0) or 0) else "SOURCE_ADAPTER_PRIORITY_FIXTURE_PACK_DISPATCH_RECEIPTS_NEED_REVIEW",
        "fixture_pack_dispatch_receipt_count": len(rows),
        "fixture_pack_execution_row_count": execution_matrix.get("fixture_pack_execution_row_count", 0),
        "dispatch_receipt_rows": rows,
    }


def _build_gui_installation_checklist(catalog: Mapping[str, Any], runtime_package: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    route_rows = _route_rows(runtime_package)
    rows: list[dict[str, Any]] = []
    for index, route in enumerate(route_rows):
        route_id = str(route.get("route_id") or "")
        rows.append({
            "schema_version": "source_adapter_priority_fixture_pack_gui_installation_row_v1",
            "row_index": index,
            "gui_installation_row_id": stable_id("source_adapter.fixture_pack_gui_installation", {"route": route_id, "index": index}),
            "route_id": route_id,
            "surface_id": route.get("surface_id"),
            "controller_entrypoint": route.get("controller_entrypoint"),
            "fixture_pack_catalog_status": catalog.get("fixture_pack_catalog_status"),
            "install_target": "runtime_source_adapter_panel" if not route_id.startswith("keys_accounts") else "keys_accounts_panel",
            "keys_accounts_label": "KEYS/ACCOUNTS",
            "installation_status": "READY_FOR_GUI_CONTROLLER_CALL_SITE" if not issues else "NEEDS_GUI_CONTROLLER_REVIEW",
        })
    return {
        "schema_version": GUI_INSTALLATION_SCHEMA_VERSION,
        "gui_installation_checklist_status": "SOURCE_ADAPTER_PRIORITY_FIXTURE_PACK_GUI_INSTALLATION_READY" if rows and not issues else "SOURCE_ADAPTER_PRIORITY_FIXTURE_PACK_GUI_INSTALLATION_NEEDS_REVIEW",
        "gui_installation_row_count": len(rows),
        "fixture_pack_count": catalog.get("fixture_pack_count", 0),
        "gui_installation_rows": rows,
    }


def _build_named_site_smoke_queue(catalog: Mapping[str, Any], runtime_package: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    provider_rows = _provider_rows(runtime_package)
    provider_ids = [str(row.get("provider_execution_adapter_id")) for row in provider_rows]
    rows: list[dict[str, Any]] = []
    for index, pack in enumerate(_rows(catalog, "fixture_pack_rows")):
        seed = {"fixture_pack_id": pack.get("fixture_pack_id"), "index": index}
        rows.append({
            "schema_version": "source_adapter_priority_fixture_pack_named_site_smoke_row_v1",
            "row_index": index,
            "named_site_smoke_queue_row_id": stable_id("source_adapter.named_site_smoke_queue", seed),
            "fixture_pack_id": pack.get("fixture_pack_id"),
            "adapter_id": pack.get("adapter_id"),
            "source_kind": pack.get("source_kind"),
            "fixture_family": pack.get("fixture_family"),
            "operator_named_site_required": True,
            "operator_approval_required": True,
            "provider_execution_adapter_ids": provider_ids,
            "required_operator_inputs": ["named_site_id", "source_url_or_local_fixture_ref", "capture_profile", "operator_approval_id", "receipt_output_dir"],
            "receipt_capture_required": True,
            "execution_mode": OPERATOR_APPROVED_MODE,
            "queue_status": "READY_FOR_OPERATOR_NAMED_SITE_INPUT_AND_APPROVAL" if not issues else "NEEDS_QUEUE_REVIEW",
        })
    return {
        "schema_version": NAMED_SITE_SMOKE_SCHEMA_VERSION,
        "named_site_smoke_queue_status": "SOURCE_ADAPTER_PRIORITY_FIXTURE_PACK_NAMED_SITE_SMOKE_QUEUE_READY" if rows and not issues else "SOURCE_ADAPTER_PRIORITY_FIXTURE_PACK_NAMED_SITE_SMOKE_QUEUE_NEEDS_REVIEW",
        "named_site_smoke_queue_count": len(rows),
        "operator_approval_required": True,
        "receipt_capture_required": True,
        "named_site_smoke_queue_rows": rows,
    }


def _build_handoff(implementation_id: str, catalog: Mapping[str, Any], execution_matrix: Mapping[str, Any], dispatch_receipts: Mapping[str, Any], gui_checklist: Mapping[str, Any], named_site_queue: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ready = (
        not issues
        and catalog.get("fixture_pack_catalog_status") == "SOURCE_ADAPTER_PRIORITY_FIXTURE_PACK_CATALOG_READY"
        and execution_matrix.get("fixture_pack_execution_matrix_status") == "SOURCE_ADAPTER_PRIORITY_FIXTURE_PACK_EXECUTION_MATRIX_READY"
        and dispatch_receipts.get("fixture_pack_dispatch_receipt_batch_status") == "SOURCE_ADAPTER_PRIORITY_FIXTURE_PACK_DISPATCH_RECEIPTS_ACCEPTED"
        and gui_checklist.get("gui_installation_checklist_status") == "SOURCE_ADAPTER_PRIORITY_FIXTURE_PACK_GUI_INSTALLATION_READY"
        and named_site_queue.get("named_site_smoke_queue_status") == "SOURCE_ADAPTER_PRIORITY_FIXTURE_PACK_NAMED_SITE_SMOKE_QUEUE_READY"
    )
    return {
        "schema_version": HANDOFF_SCHEMA_VERSION,
        "handoff_status": HANDOFF_STATUS if ready else BLOCKED_STATUS,
        "source_adapter_priority_fixture_pack_implementation_id": implementation_id,
        "ready_for_priority_fixture_regression_promotion": ready,
        "ready_for_gui_controller_fixture_pack_installation": ready,
        "ready_for_provider_dry_run_fixture_execution": ready,
        "ready_for_operator_named_site_live_smoke": ready,
        "required_next_stage": "priority_fixture_pack_regression_and_operator_live_smoke_capture" if ready else "priority_fixture_pack_implementation_review",
        "fixture_pack_count": catalog.get("fixture_pack_count", 0),
        "fixture_pack_execution_row_count": execution_matrix.get("fixture_pack_execution_row_count", 0),
        "dispatch_receipt_count": dispatch_receipts.get("fixture_pack_dispatch_receipt_count", 0),
        "named_site_smoke_queue_count": named_site_queue.get("named_site_smoke_queue_count", 0),
    }


def build_source_adapter_priority_fixture_pack_implementation(
    runtime_gui_provider_implementation_package: Mapping[str, Any],
    *,
    operator_id: str = "operator",
    fixture_pack_notes: Sequence[str] | None = None,
) -> SourceAdapterPriorityFixturePackImplementation:
    runtime_package = as_mapping(runtime_gui_provider_implementation_package, "runtime_gui_provider_implementation_package")
    issues = _validate_runtime_gui_package(runtime_package)
    catalog = _build_fixture_pack_catalog(runtime_package, issues, fixture_pack_notes or [])
    execution_matrix = _build_execution_matrix(catalog, runtime_package, issues)
    dispatch_receipts = _build_dispatch_receipts(execution_matrix, runtime_package, operator_id, issues)
    gui_checklist = _build_gui_installation_checklist(catalog, runtime_package, issues)
    named_site_queue = _build_named_site_smoke_queue(catalog, runtime_package, issues)
    implementation_id = stable_id("source_adapter.priority_fixture_pack_implementation", {
        "runtime_gui_provider_implementation_id": runtime_package.get("source_adapter_runtime_gui_provider_implementation_id"),
        "operator_id": operator_id,
        "fixture_pack_count": catalog.get("fixture_pack_count"),
        "dispatch_receipt_count": dispatch_receipts.get("fixture_pack_dispatch_receipt_count"),
    })
    handoff = _build_handoff(implementation_id, catalog, execution_matrix, dispatch_receipts, gui_checklist, named_site_queue, issues)
    ready = handoff.get("handoff_status") == HANDOFF_STATUS
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": STATUS if ready else BLOCKED_STATUS,
        "fixture_pack_count": catalog.get("fixture_pack_count", 0),
        "fixture_pack_execution_row_count": execution_matrix.get("fixture_pack_execution_row_count", 0),
        "dispatch_receipt_count": dispatch_receipts.get("fixture_pack_dispatch_receipt_count", 0),
        "named_site_smoke_queue_count": named_site_queue.get("named_site_smoke_queue_count", 0),
        "keys_accounts_label": "KEYS/ACCOUNTS",
        "next_actions": [
            "Promote accepted priority fixture pack dispatch receipts into the regular regression queue.",
            "Install GUI/controller call sites against the fixture-pack GUI installation checklist.",
            "Run named-site smoke rows only with operator approval and preserved receipts.",
            "Keep KEYS/ACCOUNTS credential references and redacted reference hashes in all smoke receipts.",
        ],
    }
    package = {
        "schema_version": SCHEMA_VERSION,
        "priority_fixture_pack_implementation_status": STATUS if ready else BLOCKED_STATUS,
        "source_adapter_priority_fixture_pack_implementation_id": implementation_id,
        "source_adapter_runtime_gui_provider_implementation_id": runtime_package.get("source_adapter_runtime_gui_provider_implementation_id"),
        "operator_id": str(operator_id),
        "issue_count": len(issues),
        "issues": list(issues),
        "implementation_logic": {
            "input_source": "source_adapter_runtime_gui_provider_implementation",
            "priority_fixture_pack_catalog_built": True,
            "fixture_pack_execution_matrix_built": True,
            "local_runtime_dispatch_receipts_recorded": True,
            "gui_controller_installation_checklist_built": True,
            "operator_named_site_smoke_queue_built": True,
            "keys_accounts_surface_preserved": True,
        },
        "source_adapter_priority_fixture_pack_catalog": catalog,
        "source_adapter_priority_fixture_pack_execution_matrix": execution_matrix,
        "source_adapter_priority_fixture_pack_dispatch_receipt_batch": dispatch_receipts,
        "source_adapter_priority_fixture_pack_gui_installation_checklist": gui_checklist,
        "source_adapter_priority_fixture_pack_named_site_smoke_queue": named_site_queue,
        "source_adapter_priority_fixture_pack_implementation_handoff": handoff,
        "operator_summary": operator_summary,
    }
    return SourceAdapterPriorityFixturePackImplementation(package)


def example_priority_fixture_pack_implementation_package() -> dict[str, Any]:
    return build_source_adapter_priority_fixture_pack_implementation(
        example_runtime_gui_provider_implementation_package(),
        operator_id="example_operator",
    ).as_dict()


def main() -> None:
    package = example_priority_fixture_pack_implementation_package()
    assert package["schema_version"] == SCHEMA_VERSION
    assert package["priority_fixture_pack_implementation_status"] == STATUS
    assert package["source_adapter_priority_fixture_pack_implementation_handoff"]["handoff_status"] == HANDOFF_STATUS
    assert package["source_adapter_priority_fixture_pack_catalog"]["fixture_pack_count"] == 5
    assert package["source_adapter_priority_fixture_pack_dispatch_receipt_batch"]["fixture_pack_dispatch_receipt_count"] >= 20
    print("Source Adapter Priority Fixture Pack Implementation self-test passed.")


if __name__ == "__main__":
    main()
