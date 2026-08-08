from __future__ import annotations

import hashlib
import json
import tempfile
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from source_adapter_smoke_receipt_review_integration import (
    EVIDENCE_INTEGRATION_STATUS as SMOKE_EVIDENCE_INTEGRATION_STATUS,
    HANDOFF_STATUS as SMOKE_REVIEW_HANDOFF_STATUS,
    KEYS_ACCOUNTS_LABEL,
    example_smoke_receipt_review_integration_package,
)

SCHEMA_VERSION = "source_adapter_evidence_export_runtime_bridge_v1"
EVIDENCE_QUEUE_SCHEMA_VERSION = "source_adapter_evidence_export_queue_v1"
EVIDENCE_QUEUE_ROW_SCHEMA_VERSION = "source_adapter_evidence_export_queue_row_v1"
TOTAL_EXPORT_SCHEMA_VERSION = "source_adapter_source_total_export_runtime_package_v1"
TOTAL_EXPORT_ROW_SCHEMA_VERSION = "source_adapter_source_total_export_runtime_row_v1"
RELEASE_INDEX_SCHEMA_VERSION = "source_adapter_release_index_runtime_package_v1"
RELEASE_INDEX_ROW_SCHEMA_VERSION = "source_adapter_release_index_runtime_row_v1"
ARCHIVE_HANDOFF_SCHEMA_VERSION = "source_adapter_archive_handoff_runtime_package_v1"
ARCHIVE_HANDOFF_ROW_SCHEMA_VERSION = "source_adapter_archive_handoff_runtime_row_v1"
HANDOFF_SCHEMA_VERSION = "source_adapter_evidence_export_runtime_bridge_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_evidence_export_runtime_bridge_operator_summary_v1"

STATUS = "SOURCE_ADAPTER_EVIDENCE_EXPORT_RUNTIME_BRIDGE_BUILT"
EVIDENCE_QUEUE_STATUS = "SOURCE_ADAPTER_EVIDENCE_EXPORT_QUEUE_READY"
TOTAL_EXPORT_STATUS = "SOURCE_ADAPTER_TOTAL_EXPORT_SOURCE_PACKAGE_READY"
RELEASE_INDEX_STATUS = "SOURCE_ADAPTER_RELEASE_INDEX_RUNTIME_PACKAGE_READY"
ARCHIVE_HANDOFF_STATUS = "SOURCE_ADAPTER_ARCHIVE_HANDOFF_RUNTIME_PACKAGE_READY"
HANDOFF_STATUS = "SOURCE_ADAPTER_EVIDENCE_EXPORT_RUNTIME_BRIDGE_READY_FOR_RELEASE_ARCHIVE_DELIVERY"
BLOCKED_STATUS = "SOURCE_ADAPTER_EVIDENCE_EXPORT_RUNTIME_BRIDGE_NEEDS_REVIEW"

@dataclass(frozen=True)
class SourceAdapterEvidenceExportRuntimeBridge:
    package: dict[str, Any]
    def as_dict(self) -> dict[str, Any]:
        return deepcopy(self.package)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}.{sha256_text(value)[:12]}"


def _rows(container: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    value = container.get(key) or []
    if isinstance(value, (str, bytes, bytearray)):
        return []
    if not isinstance(value, Sequence):
        return []
    return [dict(row) for row in value if isinstance(row, Mapping)]


def _smoke_evidence_rows(review_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    integration = review_package.get("source_adapter_smoke_receipt_evidence_integration") or {}
    if not isinstance(integration, Mapping):
        return []
    return _rows(integration, "smoke_receipt_evidence_integration_rows")


def _review_decision_rows(review_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    decisions = review_package.get("source_adapter_smoke_receipt_review_decision_batch") or {}
    if not isinstance(decisions, Mapping):
        return []
    return _rows(decisions, "smoke_receipt_review_decision_rows")


def _validate_review_package(review_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    handoff = review_package.get("source_adapter_smoke_receipt_review_integration_handoff") or {}
    evidence = review_package.get("source_adapter_smoke_receipt_evidence_integration") or {}
    if not isinstance(handoff, Mapping) or handoff.get("handoff_status") != SMOKE_REVIEW_HANDOFF_STATUS:
        issues.append({"issue_id": "smoke_review_handoff_not_ready", "severity": "error", "message": "smoke receipt review handoff is not ready"})
    if not isinstance(evidence, Mapping) or evidence.get("smoke_receipt_evidence_integration_status") != SMOKE_EVIDENCE_INTEGRATION_STATUS:
        issues.append({"issue_id": "smoke_evidence_integration_not_ready", "severity": "error", "message": "smoke evidence integration is not ready"})
    if len(_smoke_evidence_rows(review_package)) != 5:
        issues.append({"issue_id": "unexpected_smoke_evidence_row_count", "severity": "error", "message": "expected five accepted smoke evidence rows"})
    if len(_review_decision_rows(review_package)) != 25:
        issues.append({"issue_id": "unexpected_review_decision_row_count", "severity": "error", "message": "expected twenty-five provider action review decisions"})
    return issues


def _build_evidence_queue(review_package: Mapping[str, Any]) -> dict[str, Any]:
    decisions_by_site: dict[str, list[dict[str, Any]]] = {}
    for decision in _review_decision_rows(review_package):
        decisions_by_site.setdefault(str(decision.get("named_site_id")), []).append(decision)
    rows: list[dict[str, Any]] = []
    for smoke_row in _smoke_evidence_rows(review_package):
        named_site_id = str(smoke_row.get("named_site_id"))
        decisions = decisions_by_site.get(named_site_id, [])
        action_ids = [row.get("smoke_receipt_review_decision_row_id") for row in decisions]
        row_payload = {
            "named_site_id": named_site_id,
            "adapter_id": smoke_row.get("adapter_id"),
            "source_kind": smoke_row.get("source_kind"),
            "actions": action_ids,
        }
        rows.append({
            "schema_version": EVIDENCE_QUEUE_ROW_SCHEMA_VERSION,
            "row_index": len(rows),
            "source_evidence_item_id": stable_id("source_adapter.evidence_item", row_payload),
            "source_smoke_receipt_evidence_integration_row_id": smoke_row.get("smoke_receipt_evidence_integration_row_id"),
            "named_site_id": named_site_id,
            "adapter_id": smoke_row.get("adapter_id"),
            "source_kind": smoke_row.get("source_kind"),
            "review_decision_row_ids": action_ids,
            "provider_action_count": len(decisions),
            "capture_receipt_present": bool(smoke_row.get("capture_receipt_present")),
            "archive_receipt_present": bool(smoke_row.get("archive_receipt_present")),
            "release_upload_receipt_present": bool(smoke_row.get("release_upload_receipt_present")),
            "file_library_receipt_present": bool(smoke_row.get("file_library_receipt_present")),
            "credential_lookup_receipt_present": bool(smoke_row.get("credential_lookup_receipt_present")),
            "evidence_item_status": "SOURCE_ADAPTER_EVIDENCE_ITEM_READY_FOR_TOTAL_EXPORT",
            "accepted_for_total_export": True,
            "accepted_for_release_index": True,
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        })
    return {
        "schema_version": EVIDENCE_QUEUE_SCHEMA_VERSION,
        "evidence_export_queue_status": EVIDENCE_QUEUE_STATUS,
        "evidence_export_queue_row_count": len(rows),
        "provider_action_review_decision_count": len(_review_decision_rows(review_package)),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "evidence_export_queue_rows": rows,
    }


def _build_total_export_package(evidence_queue: Mapping[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for evidence in _rows(evidence_queue, "evidence_export_queue_rows"):
        payload = {"evidence": evidence.get("source_evidence_item_id"), "site": evidence.get("named_site_id")}
        rows.append({
            "schema_version": TOTAL_EXPORT_ROW_SCHEMA_VERSION,
            "row_index": len(rows),
            "total_export_source_row_id": stable_id("source_adapter.total_export_source_row", payload),
            "source_evidence_item_id": evidence.get("source_evidence_item_id"),
            "named_site_id": evidence.get("named_site_id"),
            "adapter_id": evidence.get("adapter_id"),
            "source_kind": evidence.get("source_kind"),
            "artifact_roles": ["capture_receipt", "archive_receipt", "release_upload_receipt", "file_library_receipt", "credential_lookup_receipt"],
            "review_decision_row_ids": list(evidence.get("review_decision_row_ids") or []),
            "total_export_row_status": "READY_FOR_TOTAL_EXPORT_SOURCE_PACKAGE",
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        })
    manifest = {
        "schema_version": "source_adapter_source_total_export_manifest_v1",
        "total_export_manifest_id": stable_id("source_adapter.total_export_manifest", rows),
        "total_export_source_row_count": len(rows),
        "payload_sha256": sha256_text(rows),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
    }
    return {
        "schema_version": TOTAL_EXPORT_SCHEMA_VERSION,
        "total_export_source_package_status": TOTAL_EXPORT_STATUS,
        "total_export_source_row_count": len(rows),
        "source_total_export_manifest": manifest,
        "source_total_export_rows": rows,
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
    }


def _build_release_index(total_export_package: Mapping[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for total_row in _rows(total_export_package, "source_total_export_rows"):
        payload = {"total": total_row.get("total_export_source_row_id"), "site": total_row.get("named_site_id")}
        rows.append({
            "schema_version": RELEASE_INDEX_ROW_SCHEMA_VERSION,
            "row_index": len(rows),
            "release_index_runtime_row_id": stable_id("source_adapter.release_index_runtime_row", payload),
            "source_total_export_row_id": total_row.get("total_export_source_row_id"),
            "source_evidence_item_id": total_row.get("source_evidence_item_id"),
            "named_site_id": total_row.get("named_site_id"),
            "adapter_id": total_row.get("adapter_id"),
            "source_kind": total_row.get("source_kind"),
            "release_index_entry_status": "READY_FOR_RELEASE_INDEX_DELIVERY",
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        })
    return {
        "schema_version": RELEASE_INDEX_SCHEMA_VERSION,
        "release_index_runtime_package_status": RELEASE_INDEX_STATUS,
        "release_index_runtime_row_count": len(rows),
        "release_index_runtime_rows": rows,
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
    }


def _build_archive_handoff(total_export_package: Mapping[str, Any], release_index: Mapping[str, Any]) -> dict[str, Any]:
    release_by_total = {row.get("source_total_export_row_id"): row for row in _rows(release_index, "release_index_runtime_rows")}
    rows: list[dict[str, Any]] = []
    for total_row in _rows(total_export_package, "source_total_export_rows"):
        release_row = release_by_total.get(total_row.get("total_export_source_row_id"), {})
        payload = {"total": total_row.get("total_export_source_row_id"), "release": release_row.get("release_index_runtime_row_id")}
        rows.append({
            "schema_version": ARCHIVE_HANDOFF_ROW_SCHEMA_VERSION,
            "row_index": len(rows),
            "archive_handoff_runtime_row_id": stable_id("source_adapter.archive_handoff_runtime_row", payload),
            "source_total_export_row_id": total_row.get("total_export_source_row_id"),
            "release_index_runtime_row_id": release_row.get("release_index_runtime_row_id"),
            "named_site_id": total_row.get("named_site_id"),
            "adapter_id": total_row.get("adapter_id"),
            "source_kind": total_row.get("source_kind"),
            "archive_handoff_status": "READY_FOR_ARCHIVE_DELIVERY_RUNTIME",
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        })
    return {
        "schema_version": ARCHIVE_HANDOFF_SCHEMA_VERSION,
        "archive_handoff_runtime_package_status": ARCHIVE_HANDOFF_STATUS,
        "archive_handoff_runtime_row_count": len(rows),
        "archive_handoff_runtime_rows": rows,
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
    }


def build_source_adapter_evidence_export_runtime_bridge(
    review_package: Mapping[str, Any] | None = None,
    *,
    operator_id: str = "operator",
    bridge_notes: Sequence[str] | None = None,
) -> SourceAdapterEvidenceExportRuntimeBridge:
    review_package = review_package or example_smoke_receipt_review_integration_package()
    issues = _validate_review_package(review_package)
    evidence_queue = _build_evidence_queue(review_package)
    total_export = _build_total_export_package(evidence_queue)
    release_index = _build_release_index(total_export)
    archive_handoff = _build_archive_handoff(total_export, release_index)
    status = STATUS if not issues else BLOCKED_STATUS
    handoff_status = HANDOFF_STATUS if not issues else BLOCKED_STATUS
    package = {
        "schema_version": SCHEMA_VERSION,
        "evidence_export_runtime_bridge_status": status,
        "source_adapter_evidence_export_runtime_bridge_id": stable_id("source_adapter.evidence_export_runtime_bridge", {"queue": evidence_queue, "issues": issues}),
        "operator_id": operator_id,
        "issue_count": len(issues),
        "issues": issues,
        "bridge_logic": {
            "input_source": "source_adapter_smoke_receipt_review_integration",
            "source_evidence_queue_materialized": True,
            "total_export_source_package_materialized": True,
            "release_index_runtime_package_materialized": True,
            "archive_handoff_runtime_package_materialized": True,
            "provider_action_review_decisions_consumed": len(_review_decision_rows(review_package)),
            "keys_accounts_references_preserved_redacted": True,
        },
        "source_adapter_evidence_export_queue": evidence_queue,
        "source_adapter_total_export_source_package": total_export,
        "source_adapter_release_index_runtime_package": release_index,
        "source_adapter_archive_handoff_runtime_package": archive_handoff,
        "source_adapter_evidence_export_runtime_bridge_handoff": {
            "schema_version": HANDOFF_SCHEMA_VERSION,
            "handoff_status": handoff_status,
            "evidence_export_queue_row_count": evidence_queue["evidence_export_queue_row_count"],
            "total_export_source_row_count": total_export["total_export_source_row_count"],
            "release_index_runtime_row_count": release_index["release_index_runtime_row_count"],
            "archive_handoff_runtime_row_count": archive_handoff["archive_handoff_runtime_row_count"],
            "required_next_stage": "source_adapter_release_archive_delivery_runtime",
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        },
        "operator_summary": {
            "schema_version": SUMMARY_SCHEMA_VERSION,
            "status": status,
            "operator_id": operator_id,
            "evidence_export_queue_row_count": evidence_queue["evidence_export_queue_row_count"],
            "total_export_source_row_count": total_export["total_export_source_row_count"],
            "release_index_runtime_row_count": release_index["release_index_runtime_row_count"],
            "archive_handoff_runtime_row_count": archive_handoff["archive_handoff_runtime_row_count"],
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
            "next_actions": [
                "Run release/archive delivery runtime against the materialized evidence export package.",
                "Persist local delivery receipts for evidence queue, Total Export, release index, and archive handoff outputs.",
                "Review delivery receipts before final release completion claims.",
            ],
        },
    }
    return SourceAdapterEvidenceExportRuntimeBridge(package)


def example_evidence_export_runtime_bridge_package() -> dict[str, Any]:
    return build_source_adapter_evidence_export_runtime_bridge(bridge_notes=["example evidence export runtime bridge"]).as_dict()


def main() -> None:
    print(json.dumps(example_evidence_export_runtime_bridge_package(), indent=2, sort_keys=True, ensure_ascii=False))

if __name__ == "__main__":
    main()
