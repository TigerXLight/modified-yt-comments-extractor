from __future__ import annotations

import hashlib
import json
import tempfile
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from source_adapter_release_archive_delivery_runtime import (
    DELIVERY_RECEIPT_BATCH_STATUS,
    HANDOFF_STATUS as DELIVERY_HANDOFF_STATUS,
    KEYS_ACCOUNTS_LABEL,
    example_release_archive_delivery_runtime_package,
)

SCHEMA_VERSION = "source_adapter_operator_delivery_receipt_closeout_v1"
REVIEW_SCHEMA_VERSION = "source_adapter_operator_delivery_receipt_review_v1"
REVIEW_ROW_SCHEMA_VERSION = "source_adapter_operator_delivery_receipt_review_row_v1"
ACCEPTANCE_SCHEMA_VERSION = "source_adapter_operator_delivery_acceptance_matrix_v1"
ACCEPTANCE_ROW_SCHEMA_VERSION = "source_adapter_operator_delivery_acceptance_row_v1"
RELEASE_GATE_SCHEMA_VERSION = "source_adapter_operator_delivery_release_gate_v1"
HANDOFF_SCHEMA_VERSION = "source_adapter_operator_delivery_receipt_closeout_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_operator_delivery_receipt_closeout_summary_v1"

STATUS = "SOURCE_ADAPTER_OPERATOR_DELIVERY_RECEIPT_CLOSEOUT_BUILT"
REVIEW_STATUS = "SOURCE_ADAPTER_OPERATOR_DELIVERY_RECEIPTS_REVIEWED"
ACCEPTANCE_STATUS = "SOURCE_ADAPTER_OPERATOR_DELIVERY_ACCEPTANCE_MATRIX_READY"
RELEASE_GATE_STATUS = "SOURCE_ADAPTER_OPERATOR_DELIVERY_RELEASE_GATE_READY"
HANDOFF_STATUS = "SOURCE_ADAPTER_OPERATOR_DELIVERY_RECEIPT_CLOSEOUT_READY_FOR_RELEASE_SECTION_COMPLETION"
BLOCKED_STATUS = "SOURCE_ADAPTER_OPERATOR_DELIVERY_RECEIPT_CLOSEOUT_NEEDS_REVIEW"

@dataclass(frozen=True)
class SourceAdapterOperatorDeliveryReceiptCloseout:
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
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        return []
    return [dict(row) for row in value if isinstance(row, Mapping)]


def _delivery_receipt_rows(delivery_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    batch = delivery_package.get("source_adapter_release_archive_delivery_receipt_batch") or {}
    if not isinstance(batch, Mapping):
        return []
    return _rows(batch, "release_archive_delivery_receipt_rows")


def _validate_delivery_package(delivery_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    handoff = delivery_package.get("source_adapter_release_archive_delivery_runtime_handoff") or {}
    batch = delivery_package.get("source_adapter_release_archive_delivery_receipt_batch") or {}
    if not isinstance(handoff, Mapping) or handoff.get("handoff_status") != DELIVERY_HANDOFF_STATUS:
        issues.append({"issue_id": "delivery_handoff_not_ready", "severity": "error"})
    if not isinstance(batch, Mapping) or batch.get("release_archive_delivery_receipt_batch_status") != DELIVERY_RECEIPT_BATCH_STATUS:
        issues.append({"issue_id": "delivery_receipt_batch_not_ready", "severity": "error"})
    if len(_delivery_receipt_rows(delivery_package)) != 20:
        issues.append({"issue_id": "unexpected_delivery_receipt_count", "severity": "error", "expected": 20})
    return issues


def _build_receipt_review(delivery_package: Mapping[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for receipt in _delivery_receipt_rows(delivery_package):
        path = Path(str(receipt.get("delivery_output_path")))
        accepted = bool(receipt.get("delivery_execution_performed")) and bool(receipt.get("delivery_output_exists")) and path.exists()
        rows.append({
            "schema_version": REVIEW_ROW_SCHEMA_VERSION,
            "row_index": len(rows),
            "operator_delivery_receipt_review_row_id": stable_id("source_adapter.operator_delivery_receipt_review", receipt),
            "source_release_archive_delivery_receipt_row_id": receipt.get("release_archive_delivery_receipt_row_id"),
            "named_site_id": receipt.get("named_site_id"),
            "adapter_id": receipt.get("adapter_id"),
            "source_kind": receipt.get("source_kind"),
            "delivery_target": receipt.get("delivery_target"),
            "delivery_output_path": str(path),
            "delivery_output_exists": path.exists(),
            "delivery_output_sha256": receipt.get("delivery_output_sha256"),
            "delivery_output_byte_count": receipt.get("delivery_output_byte_count"),
            "review_decision": "ACCEPTED_FOR_RELEASE_SECTION_COMPLETION" if accepted else "NEEDS_OPERATOR_DELIVERY_REVIEW",
            "accepted_for_release_section_completion": accepted,
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        })
    return {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "operator_delivery_receipt_review_status": REVIEW_STATUS,
        "operator_delivery_receipt_review_row_count": len(rows),
        "accepted_delivery_receipt_count": sum(1 for row in rows if row["accepted_for_release_section_completion"]),
        "needs_review_delivery_receipt_count": sum(1 for row in rows if not row["accepted_for_release_section_completion"]),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "operator_delivery_receipt_review_rows": rows,
    }


def _build_acceptance_matrix(review: Mapping[str, Any]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in _rows(review, "operator_delivery_receipt_review_rows"):
        grouped.setdefault(str(row.get("named_site_id")), []).append(row)
    rows: list[dict[str, Any]] = []
    for site_id, reviews in sorted(grouped.items()):
        targets = sorted(str(row.get("delivery_target")) for row in reviews)
        accepted = len(reviews) == 4 and all(row.get("accepted_for_release_section_completion") for row in reviews)
        rows.append({
            "schema_version": ACCEPTANCE_ROW_SCHEMA_VERSION,
            "row_index": len(rows),
            "operator_delivery_acceptance_row_id": stable_id("source_adapter.operator_delivery_acceptance", {"site": site_id, "targets": targets}),
            "named_site_id": site_id,
            "adapter_id": reviews[0].get("adapter_id") if reviews else None,
            "source_kind": reviews[0].get("source_kind") if reviews else None,
            "delivery_target_count": len(targets),
            "delivery_targets": targets,
            "review_row_ids": [row.get("operator_delivery_receipt_review_row_id") for row in reviews],
            "accepted_delivery_receipt_count": sum(1 for row in reviews if row.get("accepted_for_release_section_completion")),
            "accepted_for_release_section_completion": accepted,
            "accepted_for_source_evidence_release_completion": accepted,
            "accepted_for_total_export_completion": accepted,
            "accepted_for_archive_handoff_completion": accepted,
            "acceptance_status": "ACCEPTED_FOR_RELEASE_SECTION_COMPLETION" if accepted else "NEEDS_OPERATOR_DELIVERY_REVIEW",
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        })
    return {
        "schema_version": ACCEPTANCE_SCHEMA_VERSION,
        "operator_delivery_acceptance_matrix_status": ACCEPTANCE_STATUS,
        "operator_delivery_acceptance_row_count": len(rows),
        "accepted_delivery_acceptance_row_count": sum(1 for row in rows if row["accepted_for_release_section_completion"]),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "operator_delivery_acceptance_rows": rows,
    }


def _build_release_gate(acceptance: Mapping[str, Any]) -> dict[str, Any]:
    rows = _rows(acceptance, "operator_delivery_acceptance_rows")
    accepted = len(rows) == 5 and all(row.get("accepted_for_release_section_completion") for row in rows)
    return {
        "schema_version": RELEASE_GATE_SCHEMA_VERSION,
        "operator_delivery_release_gate_status": RELEASE_GATE_STATUS if accepted else "SOURCE_ADAPTER_OPERATOR_DELIVERY_RELEASE_GATE_NEEDS_REVIEW",
        "accepted_for_release_section_completion": accepted,
        "accepted_named_site_count": sum(1 for row in rows if row.get("accepted_for_release_section_completion")),
        "expected_named_site_count": 5,
        "release_section_completion_ready": accepted,
        "source_evidence_release_completion_ready": accepted,
        "total_export_completion_ready": accepted,
        "archive_handoff_completion_ready": accepted,
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
    }


def build_source_adapter_operator_delivery_receipt_closeout(
    delivery_package: Mapping[str, Any] | None = None,
    *,
    operator_id: str = "operator",
    closeout_notes: Sequence[str] | None = None,
) -> SourceAdapterOperatorDeliveryReceiptCloseout:
    delivery_package = delivery_package or example_release_archive_delivery_runtime_package()
    issues = _validate_delivery_package(delivery_package)
    review = _build_receipt_review(delivery_package)
    acceptance = _build_acceptance_matrix(review)
    release_gate = _build_release_gate(acceptance)
    if release_gate["accepted_for_release_section_completion"] is not True:
        issues.append({"issue_id": "release_gate_not_accepted", "severity": "error"})
    status = STATUS if not issues else BLOCKED_STATUS
    handoff_status = HANDOFF_STATUS if not issues else BLOCKED_STATUS
    package = {
        "schema_version": SCHEMA_VERSION,
        "operator_delivery_receipt_closeout_status": status,
        "source_adapter_operator_delivery_receipt_closeout_id": stable_id("source_adapter.operator_delivery_receipt_closeout", {"review": review, "gate": release_gate, "issues": issues}),
        "operator_id": operator_id,
        "issue_count": len(issues),
        "issues": issues,
        "closeout_logic": {
            "input_source": "source_adapter_release_archive_delivery_runtime",
            "delivery_receipts_reviewed": True,
            "release_acceptance_matrix_built": True,
            "release_section_gate_built": True,
            "keys_accounts_references_preserved_redacted": True,
        },
        "source_adapter_operator_delivery_receipt_review": review,
        "source_adapter_operator_delivery_acceptance_matrix": acceptance,
        "source_adapter_operator_delivery_release_gate": release_gate,
        "source_adapter_operator_delivery_receipt_closeout_handoff": {
            "schema_version": HANDOFF_SCHEMA_VERSION,
            "handoff_status": handoff_status,
            "operator_delivery_receipt_review_row_count": review["operator_delivery_receipt_review_row_count"],
            "operator_delivery_acceptance_row_count": acceptance["operator_delivery_acceptance_row_count"],
            "accepted_delivery_receipt_count": review["accepted_delivery_receipt_count"],
            "release_section_completion_ready": release_gate["release_section_completion_ready"],
            "required_next_stage": "source_adapter_release_section_completion_wiring",
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        },
        "operator_summary": {
            "schema_version": SUMMARY_SCHEMA_VERSION,
            "status": status,
            "operator_id": operator_id,
            "delivery_receipt_review_row_count": review["operator_delivery_receipt_review_row_count"],
            "delivery_acceptance_row_count": acceptance["operator_delivery_acceptance_row_count"],
            "accepted_named_site_count": release_gate["accepted_named_site_count"],
            "release_section_completion_ready": release_gate["release_section_completion_ready"],
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
            "next_actions": [
                "Wire accepted delivery closeout into release section completion.",
                "Expose accepted source evidence / Total Export / archive handoff outputs to the operator UI.",
                "Keep KEYS/ACCOUNTS references redacted in release completion receipts.",
            ],
        },
    }
    return SourceAdapterOperatorDeliveryReceiptCloseout(package)


def example_operator_delivery_receipt_closeout_package() -> dict[str, Any]:
    return build_source_adapter_operator_delivery_receipt_closeout(closeout_notes=["example operator delivery receipt closeout"]).as_dict()


def main() -> None:
    print(json.dumps(example_operator_delivery_receipt_closeout_package(), indent=2, sort_keys=True, ensure_ascii=False))

if __name__ == "__main__":
    main()
