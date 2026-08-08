from __future__ import annotations

import hashlib
import json
import tempfile
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from source_adapter_named_site_smoke_execution import (
    ACTION_RECEIPT_BATCH_STATUS,
    HANDOFF_STATUS as SMOKE_EXECUTION_HANDOFF_STATUS,
    KEYS_ACCOUNTS_LABEL,
    example_named_site_smoke_execution_package,
)

SCHEMA_VERSION = "source_adapter_smoke_receipt_review_integration_v1"
DECISION_BATCH_SCHEMA_VERSION = "source_adapter_smoke_receipt_review_decision_batch_v1"
DECISION_ROW_SCHEMA_VERSION = "source_adapter_smoke_receipt_review_decision_row_v1"
EVIDENCE_INTEGRATION_SCHEMA_VERSION = "source_adapter_smoke_receipt_evidence_integration_v1"
EVIDENCE_INTEGRATION_ROW_SCHEMA_VERSION = "source_adapter_smoke_receipt_evidence_integration_row_v1"
RELEASE_GATE_SCHEMA_VERSION = "source_adapter_smoke_receipt_release_export_gate_v1"
HANDOFF_SCHEMA_VERSION = "source_adapter_smoke_receipt_review_integration_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_smoke_receipt_review_integration_operator_summary_v1"

STATUS = "SOURCE_ADAPTER_SMOKE_RECEIPT_REVIEW_INTEGRATION_BUILT"
DECISION_BATCH_STATUS = "SOURCE_ADAPTER_SMOKE_RECEIPT_REVIEW_DECISIONS_READY"
EVIDENCE_INTEGRATION_STATUS = "SOURCE_ADAPTER_SMOKE_RECEIPTS_INTEGRATED_FOR_SOURCE_EVIDENCE_REVIEW"
RELEASE_GATE_STATUS = "SOURCE_ADAPTER_SMOKE_RECEIPT_RELEASE_EXPORT_GATE_READY"
HANDOFF_STATUS = "SOURCE_ADAPTER_SMOKE_RECEIPT_REVIEW_READY_FOR_RELEASE_EXPORT_INTEGRATION"
BLOCKED_STATUS = "SOURCE_ADAPTER_SMOKE_RECEIPT_REVIEW_INTEGRATION_NEEDS_REVIEW"


@dataclass(frozen=True)
class SourceAdapterSmokeReceiptReviewIntegration:
    package: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return deepcopy(self.package)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def short_hash(value: Any, length: int = 12) -> str:
    return sha256_text(value)[:length]


def stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}.{short_hash(value)}"


def _rows(container: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    value = container.get(key) or []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [dict(row) for row in value if isinstance(row, Mapping)]


def _action_receipt_rows(smoke_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    batch = smoke_package.get("source_adapter_named_site_provider_action_receipt_batch") or {}
    if not isinstance(batch, Mapping):
        return []
    return _rows(batch, "named_site_provider_action_receipt_rows")


def _site_rows(smoke_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    matrix = smoke_package.get("source_adapter_named_site_smoke_execution_matrix") or {}
    if not isinstance(matrix, Mapping):
        return []
    return _rows(matrix, "named_site_smoke_execution_site_rows")


def _validate_smoke_package(smoke_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    handoff = smoke_package.get("source_adapter_named_site_smoke_execution_handoff") or {}
    batch = smoke_package.get("source_adapter_named_site_provider_action_receipt_batch") or {}
    if not isinstance(handoff, Mapping) or handoff.get("handoff_status") != SMOKE_EXECUTION_HANDOFF_STATUS:
        issues.append({"issue_id": "smoke_execution_handoff_not_ready", "severity": "error", "message": "named-site smoke execution handoff was not ready"})
    if not isinstance(batch, Mapping) or batch.get("named_site_provider_action_receipt_batch_status") != ACTION_RECEIPT_BATCH_STATUS:
        issues.append({"issue_id": "smoke_action_receipts_not_ready", "severity": "error", "message": "named-site provider action receipt batch was not ready"})
    if len(_site_rows(smoke_package)) != 5:
        issues.append({"issue_id": "unexpected_site_count", "severity": "error", "message": "expected five named-site rows"})
    if len(_action_receipt_rows(smoke_package)) != 25:
        issues.append({"issue_id": "unexpected_action_receipt_count", "severity": "error", "message": "expected 25 provider action receipt rows"})
    return issues


def _receipt_file_status(row: Mapping[str, Any]) -> tuple[bool, str | None]:
    path_value = row.get("provider_receipt_path")
    if not path_value:
        return False, None
    path = Path(str(path_value))
    if not path.exists():
        return False, str(path)
    return True, str(path)


def _build_review_decisions(smoke_package: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for receipt in _action_receipt_rows(smoke_package):
        exists, path = _receipt_file_status(receipt)
        accepted = bool(receipt.get("provider_command_execution_succeeded")) and exists and not receipt.get("raw_credential_material_stored")
        rows.append({
            "schema_version": DECISION_ROW_SCHEMA_VERSION,
            "row_index": len(rows),
            "smoke_receipt_review_decision_row_id": stable_id("source_adapter.smoke_receipt_review_decision", receipt),
            "source_named_site_provider_action_receipt_id": receipt.get("named_site_provider_action_receipt_id"),
            "named_site_id": receipt.get("named_site_id"),
            "adapter_id": receipt.get("adapter_id"),
            "source_kind": receipt.get("source_kind"),
            "provider_action": receipt.get("provider_action"),
            "provider_receipt_path": path,
            "provider_receipt_file_present": exists,
            "provider_receipt_sha256": receipt.get("provider_receipt_sha256"),
            "provider_command_execution_succeeded": bool(receipt.get("provider_command_execution_succeeded")),
            "raw_credential_material_stored": bool(receipt.get("raw_credential_material_stored")),
            "redacted_credential_reference_hash": receipt.get("redacted_credential_reference_hash"),
            "review_decision": "ACCEPTED_FOR_SOURCE_EVIDENCE_REVIEW" if accepted else "NEEDS_OPERATOR_REVIEW",
            "accepted_for_source_evidence_review": accepted,
            "accepted_for_release_export_integration": accepted,
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        })
    accepted_count = sum(1 for row in rows if row["accepted_for_source_evidence_review"])
    return {
        "schema_version": DECISION_BATCH_SCHEMA_VERSION,
        "smoke_receipt_review_decision_batch_status": DECISION_BATCH_STATUS if not issues and accepted_count == len(rows) else "SOURCE_ADAPTER_SMOKE_RECEIPT_REVIEW_DECISIONS_NEED_REVIEW",
        "smoke_receipt_review_decision_row_count": len(rows),
        "accepted_review_decision_count": accepted_count,
        "needs_review_decision_count": len(rows) - accepted_count,
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "smoke_receipt_review_decision_rows": rows,
    }


def _build_evidence_integration(decision_batch: Mapping[str, Any]) -> dict[str, Any]:
    decisions = _rows(decision_batch, "smoke_receipt_review_decision_rows")
    grouped: dict[str, list[dict[str, Any]]] = {}
    for decision in decisions:
        grouped.setdefault(str(decision.get("named_site_id")), []).append(decision)
    rows: list[dict[str, Any]] = []
    for named_site_id, site_decisions in sorted(grouped.items()):
        action_ids = [row.get("smoke_receipt_review_decision_row_id") for row in site_decisions]
        accepted = all(row.get("accepted_for_source_evidence_review") for row in site_decisions)
        rows.append({
            "schema_version": EVIDENCE_INTEGRATION_ROW_SCHEMA_VERSION,
            "row_index": len(rows),
            "smoke_receipt_evidence_integration_row_id": stable_id("source_adapter.smoke_receipt_evidence_integration", {"site": named_site_id, "decisions": action_ids}),
            "named_site_id": named_site_id,
            "adapter_id": site_decisions[0].get("adapter_id") if site_decisions else None,
            "source_kind": site_decisions[0].get("source_kind") if site_decisions else None,
            "review_decision_row_ids": action_ids,
            "reviewed_provider_action_count": len(site_decisions),
            "accepted_provider_action_count": sum(1 for row in site_decisions if row.get("accepted_for_source_evidence_review")),
            "capture_receipt_present": any(row.get("provider_action") == "browser_capture" for row in site_decisions),
            "archive_receipt_present": any(row.get("provider_action") == "archive_submit" for row in site_decisions),
            "release_upload_receipt_present": any(row.get("provider_action") == "release_upload" for row in site_decisions),
            "file_library_receipt_present": any(row.get("provider_action") == "file_library_publish" for row in site_decisions),
            "credential_lookup_receipt_present": any(row.get("provider_action") == "credential_lookup" for row in site_decisions),
            "accepted_for_source_evidence_review": accepted,
            "accepted_for_total_export_release_integration": accepted,
            "integration_status": "READY_FOR_SOURCE_EVIDENCE_REVIEW" if accepted else "NEEDS_OPERATOR_RECEIPT_REVIEW",
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        })
    accepted_count = sum(1 for row in rows if row.get("accepted_for_source_evidence_review"))
    return {
        "schema_version": EVIDENCE_INTEGRATION_SCHEMA_VERSION,
        "smoke_receipt_evidence_integration_status": EVIDENCE_INTEGRATION_STATUS if accepted_count == len(rows) else "SOURCE_ADAPTER_SMOKE_RECEIPTS_NEED_OPERATOR_REVIEW_BEFORE_SOURCE_EVIDENCE_INTEGRATION",
        "smoke_receipt_evidence_integration_row_count": len(rows),
        "accepted_evidence_integration_row_count": accepted_count,
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "smoke_receipt_evidence_integration_rows": rows,
    }


def _build_release_gate(decision_batch: Mapping[str, Any], evidence_integration: Mapping[str, Any]) -> dict[str, Any]:
    ready = (
        decision_batch.get("smoke_receipt_review_decision_batch_status") == DECISION_BATCH_STATUS
        and evidence_integration.get("smoke_receipt_evidence_integration_status") == EVIDENCE_INTEGRATION_STATUS
    )
    return {
        "schema_version": RELEASE_GATE_SCHEMA_VERSION,
        "release_export_gate_status": RELEASE_GATE_STATUS if ready else "SOURCE_ADAPTER_SMOKE_RECEIPT_RELEASE_EXPORT_GATE_NEEDS_REVIEW",
        "ready_for_release_export_integration": ready,
        "accepted_review_decision_count": decision_batch.get("accepted_review_decision_count", 0),
        "accepted_evidence_integration_row_count": evidence_integration.get("accepted_evidence_integration_row_count", 0),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "next_stage": "source_evidence_total_export_release_integration" if ready else "operator_receipt_review",
    }


def build_source_adapter_smoke_receipt_review_integration(
    smoke_execution_package: Mapping[str, Any] | None = None,
    *,
    operator_id: str = "operator",
    review_notes: Sequence[str] | None = None,
) -> SourceAdapterSmokeReceiptReviewIntegration:
    smoke_execution_package = smoke_execution_package or example_named_site_smoke_execution_package()
    issues = _validate_smoke_package(smoke_execution_package)
    decision_batch = _build_review_decisions(smoke_execution_package, issues)
    evidence_integration = _build_evidence_integration(decision_batch)
    release_gate = _build_release_gate(decision_batch, evidence_integration)
    if not release_gate.get("ready_for_release_export_integration"):
        issues.append({"issue_id": "release_export_gate_not_ready", "severity": "error", "message": "smoke receipts are not ready for release/export integration"})
    handoff = {
        "schema_version": HANDOFF_SCHEMA_VERSION,
        "handoff_status": HANDOFF_STATUS if not issues else BLOCKED_STATUS,
        "smoke_receipt_review_decision_row_count": decision_batch.get("smoke_receipt_review_decision_row_count"),
        "smoke_receipt_evidence_integration_row_count": evidence_integration.get("smoke_receipt_evidence_integration_row_count"),
        "ready_for_release_export_integration": release_gate.get("ready_for_release_export_integration"),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": STATUS if not issues else BLOCKED_STATUS,
        "operator_id": operator_id,
        "smoke_receipt_review_decision_row_count": decision_batch.get("smoke_receipt_review_decision_row_count"),
        "accepted_review_decision_count": decision_batch.get("accepted_review_decision_count"),
        "smoke_receipt_evidence_integration_row_count": evidence_integration.get("smoke_receipt_evidence_integration_row_count"),
        "ready_for_release_export_integration": release_gate.get("ready_for_release_export_integration"),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "next_actions": [
            "Import accepted smoke receipts into source evidence review records.",
            "Attach reviewed capture/archive/release/file-library receipts to total export release surfaces.",
            "Keep KEYS/ACCOUNTS references redacted in downstream release artifacts.",
        ],
    }
    package = {
        "schema_version": SCHEMA_VERSION,
        "smoke_receipt_review_integration_status": STATUS if not issues else BLOCKED_STATUS,
        "source_named_site_smoke_execution_id": smoke_execution_package.get("source_adapter_named_site_smoke_execution_id"),
        "operator_id": operator_id,
        "review_notes": list(review_notes or []),
        "issue_count": len(issues),
        "issues": list(issues),
        "source_adapter_smoke_receipt_review_decision_batch": decision_batch,
        "source_adapter_smoke_receipt_evidence_integration": evidence_integration,
        "source_adapter_smoke_receipt_release_export_gate": release_gate,
        "source_adapter_smoke_receipt_review_integration_handoff": handoff,
        "operator_summary": operator_summary,
    }
    package["source_adapter_smoke_receipt_review_integration_id"] = stable_id("source_adapter.smoke_receipt_review_integration", package)
    return SourceAdapterSmokeReceiptReviewIntegration(package)


def example_smoke_receipt_review_integration_package() -> dict[str, Any]:
    return build_source_adapter_smoke_receipt_review_integration(
        operator_id="example_operator",
        review_notes=["deterministic smoke receipt review integration example"],
    ).as_dict()


if __name__ == "__main__":
    print(json.dumps(example_smoke_receipt_review_integration_package(), indent=2, sort_keys=True))
