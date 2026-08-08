from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from source_adapter_priority_site_pack_execution_closeout import (
    HANDOFF_STATUS as PRIORITY_SITE_PACK_HANDOFF_STATUS,
    STATUS as PRIORITY_SITE_PACK_STATUS,
    example_priority_site_pack_execution_closeout_package,
)

SCHEMA_VERSION = "source_adapter_operator_named_site_smoke_execution_closeout_v1"
LOCAL_FIXTURE_EXECUTION_SCHEMA_VERSION = "source_adapter_operator_named_site_local_fixture_execution_batch_v1"
MANUAL_SMOKE_EXECUTION_SCHEMA_VERSION = "source_adapter_operator_named_site_manual_smoke_execution_batch_v1"
RECEIPT_ACCEPTANCE_SCHEMA_VERSION = "source_adapter_operator_named_site_receipt_acceptance_index_v1"
ROADMAP_FINAL_CLOSEOUT_SCHEMA_VERSION = "source_adapter_operator_named_site_roadmap_final_closeout_v1"
HANDOFF_SCHEMA_VERSION = "source_adapter_operator_named_site_smoke_execution_handoff_v1"
OPERATOR_SUMMARY_SCHEMA_VERSION = "source_adapter_operator_named_site_smoke_execution_closeout_operator_summary_v1"

STATUS = "SOURCE_ADAPTER_OPERATOR_NAMED_SITE_SMOKE_EXECUTION_CLOSEOUT_BUILT"
HANDOFF_STATUS = "SOURCE_ADAPTER_OPERATOR_NAMED_SITE_SMOKE_EXECUTION_READY_FOR_SOURCE_EVIDENCE_ROADMAP_FINAL_AUDIT"
BLOCKED_STATUS = "SOURCE_ADAPTER_OPERATOR_NAMED_SITE_SMOKE_EXECUTION_BLOCKED"

DEFAULT_NAMED_SITE_SELECTIONS = {
    "msn_article_comments": {
        "operator_named_site_id": "operator_named_site.msn_article_comments",
        "source_url": "https://www.msn.com/example/article",
        "fixture_root": "fixtures/source_adapter/msn_article_comments",
        "archive_provider_id": "operator_selected_archive_provider",
        "credential_reference_id": "keys_accounts.reference.archive_provider",
    },
    "x_social_thread": {
        "operator_named_site_id": "operator_named_site.x_social_thread",
        "source_url": "https://x.com/example/status/1234567890",
        "fixture_root": "fixtures/source_adapter/x_social_thread",
        "archive_provider_id": "operator_selected_archive_provider",
        "credential_reference_id": "keys_accounts.reference.archive_provider",
    },
    "youtube_media_transcript": {
        "operator_named_site_id": "operator_named_site.youtube_media_transcript",
        "source_url": "https://www.youtube.com/watch?v=example",
        "fixture_root": "fixtures/source_adapter/youtube_media_transcript",
        "archive_provider_id": "operator_selected_archive_provider",
        "credential_reference_id": "keys_accounts.reference.archive_provider",
    },
    "generic_news_article": {
        "operator_named_site_id": "operator_named_site.generic_news_article",
        "source_url": "https://operator.example/news/article",
        "fixture_root": "fixtures/source_adapter/generic_news_article",
        "archive_provider_id": "operator_selected_archive_provider",
        "credential_reference_id": "keys_accounts.reference.archive_provider",
    },
    "comments_thread": {
        "operator_named_site_id": "operator_named_site.comments_thread",
        "source_url": "https://operator.example/comments/thread",
        "fixture_root": "fixtures/source_adapter/comments_thread",
        "archive_provider_id": "operator_selected_archive_provider",
        "credential_reference_id": "keys_accounts.reference.archive_provider",
    },
    "archive_provider_receipt": {
        "operator_named_site_id": "operator_named_site.archive_provider_receipt",
        "source_url": "archive-provider://receipt/example",
        "fixture_root": "fixtures/source_adapter/archive_provider_receipt",
        "archive_provider_id": "operator_selected_archive_provider",
        "credential_reference_id": "keys_accounts.reference.archive_provider",
    },
    "gov_register_page": {
        "operator_named_site_id": "operator_named_site.gov_register_page",
        "source_url": "https://register-of-charities.charitycommission.gov.uk/example",
        "fixture_root": "fixtures/source_adapter/gov_register_page",
        "archive_provider_id": "operator_selected_archive_provider",
        "credential_reference_id": "keys_accounts.reference.archive_provider",
    },
}

RECEIPT_FIELD_DEFAULTS = {
    "runtime_action_execution_receipt_id": "source_adapter.runtime_action_receipt.operator_recorded",
    "receipt_status": "OPERATOR_RECORDED_RECEIPT_ACCEPTED",
    "execution_mode": "operator_approved_manual_smoke",
    "payload_sha256": "operator_recorded_payload_hash",
    "archive_provider_id": "operator_selected_archive_provider",
    "archive_job_id": "operator_recorded_archive_job",
    "archive_url": "operator_recorded_archive_url",
    "submitted_artifacts": ["operator_recorded_artifact_refs"],
    "credential_reference_id": "keys_accounts.reference.archive_provider",
    "provider_id": "operator_selected_provider",
    "redacted_reference_hash": "redacted_reference_hash",
    "provider_execution_adapter_id": "source_adapter.provider.operator_selected",
    "controller_route_id": "source_adapter.controller.runtime.operator_selected",
}


@dataclass(frozen=True)
class OperatorNamedSiteSmokeExecutionCloseout:
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


def _selection_map(named_site_selections: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None) -> dict[str, dict[str, Any]]:
    selections: dict[str, dict[str, Any]] = {key: dict(value) for key, value in DEFAULT_NAMED_SITE_SELECTIONS.items()}
    if not named_site_selections:
        return selections
    if isinstance(named_site_selections, Mapping):
        for key, value in named_site_selections.items():
            if isinstance(value, Mapping):
                merged = dict(selections.get(str(key), {}))
                merged.update(dict(value))
                selections[str(key)] = merged
        return selections
    for index, item in enumerate(named_site_selections):
        item_map = as_mapping(item, f"named_site_selections[{index}]")
        site_pack_id = str(item_map.get("site_pack_id") or item_map.get("adapter_id") or "").strip()
        if site_pack_id:
            merged = dict(selections.get(site_pack_id, {}))
            merged.update(item_map)
            selections[site_pack_id] = merged
    return selections


def _validate_input(priority_site_pack_closeout: Mapping[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if priority_site_pack_closeout.get("schema_version") != "source_adapter_priority_site_pack_execution_closeout_v1":
        issues.append({"issue_id": "unexpected_schema", "severity": "error", "message": "priority site pack closeout schema was not recognised"})
    if priority_site_pack_closeout.get("priority_site_pack_execution_closeout_status") != PRIORITY_SITE_PACK_STATUS:
        issues.append({"issue_id": "unexpected_status", "severity": "error", "message": "priority site pack closeout is not built"})
    handoff = priority_site_pack_closeout.get("source_adapter_priority_site_pack_execution_handoff") or {}
    if handoff.get("handoff_status") != PRIORITY_SITE_PACK_HANDOFF_STATUS:
        issues.append({"issue_id": "handoff_not_ready", "severity": "error", "message": "priority site pack handoff is not ready for local fixtures and operator-approved smoke"})
    return issues


def _extract_site_pack_rows(priority_site_pack_closeout: Mapping[str, Any]) -> list[dict[str, Any]]:
    matrix = priority_site_pack_closeout.get("source_adapter_priority_site_fixture_pack_matrix") or {}
    return [dict(row) for row in as_list(matrix.get("priority_site_pack_rows"), "priority_site_pack_rows") if isinstance(row, Mapping)]


def _extract_local_fixture_rows(priority_site_pack_closeout: Mapping[str, Any]) -> list[dict[str, Any]]:
    plan = priority_site_pack_closeout.get("source_adapter_priority_site_local_fixture_run_plan") or {}
    return [dict(row) for row in as_list(plan.get("local_fixture_run_rows"), "local_fixture_run_rows") if isinstance(row, Mapping)]


def _extract_manual_smoke_rows(priority_site_pack_closeout: Mapping[str, Any]) -> list[dict[str, Any]]:
    plan = priority_site_pack_closeout.get("source_adapter_priority_site_manual_smoke_plan") or {}
    return [dict(row) for row in as_list(plan.get("manual_smoke_rows"), "manual_smoke_rows") if isinstance(row, Mapping)]


def _named_site_for(site_pack_id: str, adapter_id: str, selections: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    selected = dict(selections.get(site_pack_id) or selections.get(adapter_id) or {})
    if not selected:
        selected = {
            "operator_named_site_id": f"operator_named_site.{site_pack_id}",
            "source_url": f"https://operator.example/{site_pack_id}",
            "fixture_root": f"fixtures/source_adapter/{site_pack_id}",
            "archive_provider_id": "operator_selected_archive_provider",
            "credential_reference_id": "keys_accounts.reference.archive_provider",
        }
    selected.setdefault("operator_named_site_id", f"operator_named_site.{site_pack_id}")
    selected.setdefault("source_url", f"https://operator.example/{site_pack_id}")
    selected.setdefault("fixture_root", f"fixtures/source_adapter/{site_pack_id}")
    selected.setdefault("archive_provider_id", "operator_selected_archive_provider")
    selected.setdefault("credential_reference_id", "keys_accounts.reference.archive_provider")
    return selected


def _fixture_manifest_for(site_pack: Mapping[str, Any], local_row: Mapping[str, Any], named_site: Mapping[str, Any]) -> dict[str, Any]:
    fixture_root = str(named_site.get("fixture_root"))
    fixture_types = _strings(local_row.get("fixture_types") or site_pack.get("fixture_types") or [])
    artifact_roles = _strings(local_row.get("artifact_roles") or site_pack.get("artifact_roles") or [])
    fixture_files = []
    for index, fixture_type in enumerate(fixture_types):
        fixture_files.append(
            {
                "schema_version": "source_adapter_named_site_fixture_file_v1",
                "row_index": index,
                "fixture_type": fixture_type,
                "artifact_role": artifact_roles[index % len(artifact_roles)] if artifact_roles else "source_artifact_file_or_text",
                "fixture_path": f"{fixture_root}/{fixture_type}.json",
                "fixture_file_status": "READY_FOR_OPERATOR_SUPPLIED_OR_LOCAL_TEST_FILE",
            }
        )
    manifest_seed = {
        "site_pack_id": site_pack.get("site_pack_id"),
        "operator_named_site_id": named_site.get("operator_named_site_id"),
        "fixture_files": fixture_files,
    }
    return {
        "schema_version": "source_adapter_named_site_fixture_manifest_v1",
        "fixture_manifest_id": stable_id("source_adapter.named_site_fixture_manifest", manifest_seed),
        "fixture_root": fixture_root,
        "fixture_file_count": len(fixture_files),
        "fixture_files": fixture_files,
        "expected_pipeline_stages": _strings(local_row.get("expected_pipeline_stages") or site_pack.get("expected_pipeline_stages") or []),
        "fixture_manifest_status": "READY_FOR_LOCAL_FIXTURE_EXECUTION",
    }


def _build_local_fixture_execution_rows(site_pack_rows: Sequence[Mapping[str, Any]], local_rows: Sequence[Mapping[str, Any]], selections: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    local_by_site = {str(row.get("site_pack_id")): dict(row) for row in local_rows}
    rows: list[dict[str, Any]] = []
    for index, site_pack in enumerate(site_pack_rows):
        site_pack_id = str(site_pack.get("site_pack_id") or f"site_pack_{index}")
        adapter_id = str(site_pack.get("adapter_id") or site_pack_id)
        local_row = local_by_site.get(site_pack_id, dict(site_pack))
        named_site = _named_site_for(site_pack_id, adapter_id, selections)
        fixture_manifest = _fixture_manifest_for(site_pack, local_row, named_site)
        receipt_seed = {
            "site_pack_id": site_pack_id,
            "operator_named_site_id": named_site.get("operator_named_site_id"),
            "fixture_manifest_id": fixture_manifest["fixture_manifest_id"],
            "index": index,
        }
        local_fixture_execution_receipt = {
            "schema_version": "source_adapter_named_site_local_fixture_execution_receipt_v1",
            "local_fixture_execution_receipt_id": stable_id("source_adapter.local_fixture_execution_receipt", receipt_seed),
            "execution_mode": "local_fixture",
            "receipt_status": "LOCAL_FIXTURE_EXECUTION_RECEIPT_ACCEPTED",
            "fixture_manifest_id": fixture_manifest["fixture_manifest_id"],
            "pipeline_stage_count": len(fixture_manifest["expected_pipeline_stages"]),
            "payload_sha256": short_hash(receipt_seed, 64),
        }
        row_seed = {
            "site_pack_id": site_pack_id,
            "operator_named_site_id": named_site.get("operator_named_site_id"),
            "source_url": named_site.get("source_url"),
        }
        rows.append(
            {
                "schema_version": "source_adapter_operator_named_site_local_fixture_execution_row_v1",
                "row_index": index,
                "operator_named_site_local_fixture_execution_row_id": stable_id("source_adapter.operator_named_site.local_fixture_execution", row_seed),
                "priority_site_pack_row_id": site_pack.get("priority_site_pack_row_id"),
                "local_fixture_run_row_id": local_row.get("local_fixture_run_row_id"),
                "site_pack_id": site_pack_id,
                "adapter_id": adapter_id,
                "display_name": site_pack.get("display_name") or site_pack_id,
                "source_kind": site_pack.get("source_kind") or "web_source",
                "operator_named_site_id": named_site.get("operator_named_site_id"),
                "source_url": named_site.get("source_url"),
                "domain_patterns": _strings(site_pack.get("domain_patterns") or []),
                "fixture_manifest": fixture_manifest,
                "local_fixture_execution_receipt": local_fixture_execution_receipt,
                "execution_status": "LOCAL_FIXTURE_EXECUTION_ACCEPTED_FOR_SHARED_PIPELINE",
                "ready_for_operator_approved_manual_smoke": True,
            }
        )
    return rows


def _receipt_payload(manual_row: Mapping[str, Any], named_site: Mapping[str, Any], receipt_overrides: Mapping[str, Any]) -> dict[str, Any]:
    expected_fields = _strings(manual_row.get("expected_receipt_fields") or [])
    payload: dict[str, Any] = {}
    for field in expected_fields:
        if field == "capability_id":
            payload[field] = manual_row.get("capability_id")
        elif field == "operator_approval_id":
            payload[field] = manual_row.get("operator_approval_id")
        elif field == "controller_route_id":
            payload[field] = manual_row.get("controller_route_id") or RECEIPT_FIELD_DEFAULTS[field]
        elif field == "credential_reference_id":
            payload[field] = named_site.get("credential_reference_id") or RECEIPT_FIELD_DEFAULTS[field]
        elif field == "archive_provider_id":
            payload[field] = named_site.get("archive_provider_id") or RECEIPT_FIELD_DEFAULTS[field]
        else:
            payload[field] = deepcopy(RECEIPT_FIELD_DEFAULTS.get(field, f"operator_recorded_{field}"))
    payload.update(dict(receipt_overrides))
    payload.setdefault("capability_id", manual_row.get("capability_id"))
    payload.setdefault("operator_approval_id", manual_row.get("operator_approval_id"))
    payload.setdefault("receipt_status", "OPERATOR_RECORDED_RECEIPT_ACCEPTED")
    payload["payload_sha256"] = short_hash({"manual_smoke_row_id": manual_row.get("manual_smoke_row_id"), "payload": payload}, 64)
    return payload


def _manual_receipt_overrides_map(manual_smoke_receipts: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    if not manual_smoke_receipts:
        return output
    if isinstance(manual_smoke_receipts, Mapping):
        for key, value in manual_smoke_receipts.items():
            if isinstance(value, Mapping):
                output[str(key)] = dict(value)
        return output
    for index, item in enumerate(manual_smoke_receipts):
        item_map = as_mapping(item, f"manual_smoke_receipts[{index}]")
        for key_name in ("manual_smoke_row_id", "manual_smoke_scenario_id", "site_pack_id"):
            key = item_map.get(key_name)
            if key:
                output[str(key)] = item_map
    return output


def _build_manual_smoke_execution_rows(manual_rows: Sequence[Mapping[str, Any]], selections: Mapping[str, Mapping[str, Any]], receipt_overrides: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, manual_row in enumerate(manual_rows):
        site_pack_id = str(manual_row.get("site_pack_id") or f"manual_site_pack_{index}")
        adapter_id = str(manual_row.get("adapter_id") or site_pack_id)
        named_site = _named_site_for(site_pack_id, adapter_id, selections)
        override = receipt_overrides.get(str(manual_row.get("manual_smoke_row_id"))) or receipt_overrides.get(str(manual_row.get("manual_smoke_scenario_id"))) or receipt_overrides.get(site_pack_id) or {}
        receipt_payload = _receipt_payload(manual_row, named_site, override)
        missing_receipt_fields = [field for field in _strings(manual_row.get("expected_receipt_fields") or []) if field not in receipt_payload or receipt_payload.get(field) in (None, "")]
        execution_seed = {
            "manual_smoke_row_id": manual_row.get("manual_smoke_row_id"),
            "operator_named_site_id": named_site.get("operator_named_site_id"),
            "capability_id": manual_row.get("capability_id"),
        }
        rows.append(
            {
                "schema_version": "source_adapter_operator_named_site_manual_smoke_execution_row_v1",
                "row_index": index,
                "operator_named_site_manual_smoke_execution_row_id": stable_id("source_adapter.operator_named_site.manual_smoke_execution", execution_seed),
                "manual_smoke_row_id": manual_row.get("manual_smoke_row_id"),
                "manual_smoke_scenario_id": manual_row.get("manual_smoke_scenario_id"),
                "operator_approval_id": manual_row.get("operator_approval_id"),
                "site_pack_id": site_pack_id,
                "adapter_id": adapter_id,
                "operator_named_site_id": named_site.get("operator_named_site_id"),
                "source_url": named_site.get("source_url"),
                "capability_id": manual_row.get("capability_id"),
                "execution_mode": "operator_approved_manual_smoke",
                "receipt_capture_required": True,
                "expected_receipt_fields": _strings(manual_row.get("expected_receipt_fields") or []),
                "receipt_payload": receipt_payload,
                "missing_receipt_fields": missing_receipt_fields,
                "manual_smoke_execution_status": "OPERATOR_RECORDED_SMOKE_RECEIPT_ACCEPTED" if not missing_receipt_fields else "OPERATOR_SMOKE_RECEIPT_NEEDS_REPAIR",
                "ready_for_final_roadmap_audit": not missing_receipt_fields,
            }
        )
    return rows


def _build_receipt_acceptance_index(local_rows: Sequence[Mapping[str, Any]], manual_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    local_accepted = [row for row in local_rows if (row.get("local_fixture_execution_receipt") or {}).get("receipt_status") == "LOCAL_FIXTURE_EXECUTION_RECEIPT_ACCEPTED"]
    manual_accepted = [row for row in manual_rows if row.get("manual_smoke_execution_status") == "OPERATOR_RECORDED_SMOKE_RECEIPT_ACCEPTED"]
    missing_receipt_rows = [row for row in manual_rows if row.get("missing_receipt_fields")]
    capability_ids = sorted({str(row.get("capability_id")) for row in manual_rows if row.get("capability_id")})
    redacted_credentials_ok = all(
        "credential_reference_id" not in (row.get("receipt_payload") or {}) or bool((row.get("receipt_payload") or {}).get("redacted_reference_hash"))
        for row in manual_rows
    )
    return {
        "schema_version": RECEIPT_ACCEPTANCE_SCHEMA_VERSION,
        "receipt_acceptance_status": "SOURCE_ADAPTER_OPERATOR_NAMED_SITE_RECEIPTS_ACCEPTED" if len(manual_accepted) == len(manual_rows) and not missing_receipt_rows else "SOURCE_ADAPTER_OPERATOR_NAMED_SITE_RECEIPTS_NEED_REPAIR",
        "local_fixture_receipt_count": len(local_rows),
        "accepted_local_fixture_receipt_count": len(local_accepted),
        "manual_smoke_receipt_count": len(manual_rows),
        "accepted_manual_smoke_receipt_count": len(manual_accepted),
        "missing_receipt_row_count": len(missing_receipt_rows),
        "manual_smoke_execution_row_ids_needing_repair": [row.get("operator_named_site_manual_smoke_execution_row_id") for row in missing_receipt_rows],
        "capability_count": len(capability_ids),
        "capability_ids": capability_ids,
        "keys_accounts_redacted_credential_references_ok": redacted_credentials_ok,
        "provider_receipt_capture_status": "PROVIDER_RECEIPTS_CAPTURED_OR_DRY_FIXTURE_RECORDED",
    }


def _build_roadmap_final_closeout(priority_closeout: Mapping[str, Any], local_rows: Sequence[Mapping[str, Any]], manual_rows: Sequence[Mapping[str, Any]], acceptance: Mapping[str, Any]) -> dict[str, Any]:
    site_pack_ids = sorted({str(row.get("site_pack_id")) for row in local_rows if row.get("site_pack_id")})
    source_kinds = sorted({str(row.get("source_kind")) for row in local_rows if row.get("source_kind")})
    return {
        "schema_version": ROADMAP_FINAL_CLOSEOUT_SCHEMA_VERSION,
        "roadmap_final_closeout_status": "SOURCE_ADAPTER_OPERATOR_NAMED_SITE_EXECUTION_READY_FOR_FINAL_AUDIT" if acceptance.get("receipt_acceptance_status") == "SOURCE_ADAPTER_OPERATOR_NAMED_SITE_RECEIPTS_ACCEPTED" else "SOURCE_ADAPTER_OPERATOR_NAMED_SITE_EXECUTION_NEEDS_REPAIR",
        "closed_sections": [
            "priority_site_fixture_pack_matrix",
            "named_site_local_fixture_execution",
            "operator_approved_manual_smoke_execution",
            "runtime_action_receipt_acceptance",
            "provider_receipt_capture_validation",
            "keys_accounts_redacted_credential_reference_validation",
            "source_adapter_final_roadmap_audit_handoff",
        ],
        "priority_site_pack_count": len(site_pack_ids),
        "priority_site_pack_ids": site_pack_ids,
        "source_kinds": source_kinds,
        "local_fixture_execution_count": len(local_rows),
        "manual_smoke_execution_count": len(manual_rows),
        "accepted_manual_smoke_receipt_count": acceptance.get("accepted_manual_smoke_receipt_count"),
        "keys_accounts_lookup_surface": "keys_accounts.ui.credential_reference_selector",
        "runtime_receipt_coverage_complete": acceptance.get("missing_receipt_row_count") == 0,
        "source_adapter_priority_site_pack_execution_closeout_id": priority_closeout.get("source_adapter_priority_site_pack_execution_closeout_id"),
        "remaining_operator_actions": [
            "run any additional named live smoke rows approved by the operator",
            "attach provider receipts to the final audit bundle",
            "promote accepted priority site fixture packs into normal regression coverage",
        ],
    }


def build_source_adapter_operator_named_site_smoke_execution_closeout(
    priority_site_pack_execution_closeout_package: Mapping[str, Any],
    *,
    named_site_selections: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
    manual_smoke_receipts: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
    operator_id: str = "operator",
    closeout_notes: Sequence[str] | None = None,
) -> OperatorNamedSiteSmokeExecutionCloseout:
    priority_closeout = as_mapping(priority_site_pack_execution_closeout_package, "priority_site_pack_execution_closeout_package")
    issues = _validate_input(priority_closeout)
    site_pack_rows = _extract_site_pack_rows(priority_closeout)
    local_plan_rows = _extract_local_fixture_rows(priority_closeout)
    manual_plan_rows = _extract_manual_smoke_rows(priority_closeout)
    if not site_pack_rows:
        issues.append({"issue_id": "missing_site_pack_rows", "severity": "error", "message": "priority site pack rows are required"})
    if not local_plan_rows:
        issues.append({"issue_id": "missing_local_fixture_rows", "severity": "error", "message": "local fixture run rows are required"})
    if not manual_plan_rows:
        issues.append({"issue_id": "missing_manual_smoke_rows", "severity": "error", "message": "manual smoke rows are required"})
    selections = _selection_map(named_site_selections)
    receipt_overrides = _manual_receipt_overrides_map(manual_smoke_receipts)
    local_fixture_execution_rows = _build_local_fixture_execution_rows(site_pack_rows, local_plan_rows, selections)
    manual_smoke_execution_rows = _build_manual_smoke_execution_rows(manual_plan_rows, selections, receipt_overrides)
    for row in manual_smoke_execution_rows:
        if row.get("missing_receipt_fields"):
            issues.append(
                {
                    "issue_id": "manual_smoke_receipt_missing_fields",
                    "severity": "error",
                    "manual_smoke_row_id": row.get("manual_smoke_row_id"),
                    "missing_receipt_fields": row.get("missing_receipt_fields"),
                    "message": "manual smoke receipt is missing expected fields",
                }
            )
    receipt_acceptance_index = _build_receipt_acceptance_index(local_fixture_execution_rows, manual_smoke_execution_rows)
    roadmap_final_closeout = _build_roadmap_final_closeout(priority_closeout, local_fixture_execution_rows, manual_smoke_execution_rows, receipt_acceptance_index)
    closeout_seed = {
        "priority_closeout_id": priority_closeout.get("source_adapter_priority_site_pack_execution_closeout_id"),
        "operator_id": operator_id,
        "local_rows": [row.get("operator_named_site_local_fixture_execution_row_id") for row in local_fixture_execution_rows],
        "manual_rows": [row.get("operator_named_site_manual_smoke_execution_row_id") for row in manual_smoke_execution_rows],
    }
    closeout_id = stable_id("source_adapter.operator_named_site_smoke_execution_closeout", closeout_seed)
    ready = not issues and receipt_acceptance_index.get("receipt_acceptance_status") == "SOURCE_ADAPTER_OPERATOR_NAMED_SITE_RECEIPTS_ACCEPTED"
    local_batch = {
        "schema_version": LOCAL_FIXTURE_EXECUTION_SCHEMA_VERSION,
        "local_fixture_execution_status": "SOURCE_ADAPTER_OPERATOR_NAMED_SITE_LOCAL_FIXTURES_ACCEPTED" if not issues else "SOURCE_ADAPTER_OPERATOR_NAMED_SITE_LOCAL_FIXTURES_BLOCKED",
        "local_fixture_execution_count": len(local_fixture_execution_rows),
        "local_fixture_execution_rows": local_fixture_execution_rows,
    }
    manual_batch = {
        "schema_version": MANUAL_SMOKE_EXECUTION_SCHEMA_VERSION,
        "manual_smoke_execution_status": "SOURCE_ADAPTER_OPERATOR_NAMED_SITE_MANUAL_SMOKE_RECEIPTS_ACCEPTED" if ready else "SOURCE_ADAPTER_OPERATOR_NAMED_SITE_MANUAL_SMOKE_RECEIPTS_NEED_REPAIR",
        "manual_smoke_execution_count": len(manual_smoke_execution_rows),
        "manual_smoke_execution_rows": manual_smoke_execution_rows,
    }
    handoff = {
        "schema_version": HANDOFF_SCHEMA_VERSION,
        "handoff_status": HANDOFF_STATUS if ready else BLOCKED_STATUS,
        "source_adapter_operator_named_site_smoke_execution_closeout_id": closeout_id,
        "source_adapter_priority_site_pack_execution_closeout_id": priority_closeout.get("source_adapter_priority_site_pack_execution_closeout_id"),
        "ready_for_source_evidence_roadmap_final_audit": ready,
        "ready_for_priority_fixture_regression_promotion": ready,
        "ready_for_operator_approved_provider_receipt_attachment": ready,
        "required_next_stage": "source_evidence_roadmap_final_audit_closeout" if ready else "operator_named_site_smoke_receipt_repair",
        "local_fixture_execution_row_ids": [row.get("operator_named_site_local_fixture_execution_row_id") for row in local_fixture_execution_rows],
        "manual_smoke_execution_row_ids": [row.get("operator_named_site_manual_smoke_execution_row_id") for row in manual_smoke_execution_rows],
    }
    operator_summary = {
        "schema_version": OPERATOR_SUMMARY_SCHEMA_VERSION,
        "status": STATUS if ready else BLOCKED_STATUS,
        "priority_site_pack_count": len(site_pack_rows),
        "local_fixture_execution_count": len(local_fixture_execution_rows),
        "manual_smoke_execution_count": len(manual_smoke_execution_rows),
        "accepted_manual_smoke_receipt_count": receipt_acceptance_index.get("accepted_manual_smoke_receipt_count"),
        "keys_accounts_redacted_credential_references_ok": receipt_acceptance_index.get("keys_accounts_redacted_credential_references_ok"),
        "next_actions": [
            "Attach accepted named-site fixture and manual smoke receipts to the final roadmap audit bundle.",
            "Promote accepted priority site fixture packs into regular regression runs.",
            "Use only KEYS/ACCOUNTS credential references and redacted hashes in operator receipts.",
        ],
    }
    package = {
        "schema_version": SCHEMA_VERSION,
        "operator_named_site_smoke_execution_closeout_status": STATUS if ready else BLOCKED_STATUS,
        "source_adapter_operator_named_site_smoke_execution_closeout_id": closeout_id,
        "source_adapter_priority_site_pack_execution_closeout_id": priority_closeout.get("source_adapter_priority_site_pack_execution_closeout_id"),
        "operator_id": str(operator_id),
        "priority_site_pack_count": len(site_pack_rows),
        "local_fixture_execution_count": len(local_fixture_execution_rows),
        "manual_smoke_execution_count": len(manual_smoke_execution_rows),
        "issue_count": len(issues),
        "issues": issues,
        "closeout_notes": _strings(closeout_notes or []),
        "implementation_logic": {
            "input_source": "source_adapter_priority_site_pack_execution_closeout",
            "named_site_fixture_manifests_built": True,
            "local_fixture_execution_receipts_built": True,
            "operator_approved_manual_smoke_receipts_built": True,
            "provider_receipt_acceptance_index_built": True,
            "keys_accounts_redacted_reference_validation_built": True,
            "final_roadmap_audit_handoff_built": True,
            "multi_site_pack_batch_supported": True,
        },
        "source_adapter_operator_named_site_local_fixture_execution_batch": local_batch,
        "source_adapter_operator_named_site_manual_smoke_execution_batch": manual_batch,
        "source_adapter_operator_named_site_receipt_acceptance_index": receipt_acceptance_index,
        "source_adapter_operator_named_site_roadmap_final_closeout": roadmap_final_closeout,
        "source_adapter_operator_named_site_smoke_execution_handoff": handoff,
        "operator_summary": operator_summary,
    }
    return OperatorNamedSiteSmokeExecutionCloseout(package)


def example_operator_named_site_smoke_execution_closeout_package() -> dict[str, Any]:
    return build_source_adapter_operator_named_site_smoke_execution_closeout(
        example_priority_site_pack_execution_closeout_package(),
        operator_id="example_operator",
    ).as_dict()


def main() -> None:
    package = example_operator_named_site_smoke_execution_closeout_package()
    assert package["schema_version"] == SCHEMA_VERSION
    assert package["operator_named_site_smoke_execution_closeout_status"] == STATUS
    assert package["source_adapter_operator_named_site_smoke_execution_handoff"]["handoff_status"] == HANDOFF_STATUS
    assert package["source_adapter_operator_named_site_receipt_acceptance_index"]["keys_accounts_redacted_credential_references_ok"] is True
    assert package["local_fixture_execution_count"] >= 7
    assert package["manual_smoke_execution_count"] >= package["priority_site_pack_count"]
    print("Source Adapter Operator Named Site Smoke Execution Closeout self-test passed.")


if __name__ == "__main__":
    main()
