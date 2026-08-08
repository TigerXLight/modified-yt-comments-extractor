from __future__ import annotations

import hashlib
import json
import os
import tempfile
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from source_adapter_evidence_export_runtime_bridge import (
    HANDOFF_STATUS as EVIDENCE_EXPORT_HANDOFF_STATUS,
    KEYS_ACCOUNTS_LABEL,
    example_evidence_export_runtime_bridge_package,
)

SCHEMA_VERSION = "source_adapter_release_archive_delivery_runtime_v1"
DELIVERY_PLAN_SCHEMA_VERSION = "source_adapter_release_archive_delivery_plan_v1"
DELIVERY_PLAN_ROW_SCHEMA_VERSION = "source_adapter_release_archive_delivery_plan_row_v1"
DELIVERY_RECEIPT_BATCH_SCHEMA_VERSION = "source_adapter_release_archive_delivery_receipt_batch_v1"
DELIVERY_RECEIPT_ROW_SCHEMA_VERSION = "source_adapter_release_archive_delivery_receipt_row_v1"
HANDOFF_SCHEMA_VERSION = "source_adapter_release_archive_delivery_runtime_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_release_archive_delivery_runtime_operator_summary_v1"

STATUS = "SOURCE_ADAPTER_RELEASE_ARCHIVE_DELIVERY_RUNTIME_BUILT"
DELIVERY_PLAN_STATUS = "SOURCE_ADAPTER_RELEASE_ARCHIVE_DELIVERY_PLAN_READY"
DELIVERY_RECEIPT_BATCH_STATUS = "SOURCE_ADAPTER_RELEASE_ARCHIVE_DELIVERY_RECEIPTS_READY"
HANDOFF_STATUS = "SOURCE_ADAPTER_RELEASE_ARCHIVE_DELIVERY_RUNTIME_READY_FOR_OPERATOR_RECEIPT_CLOSEOUT"
BLOCKED_STATUS = "SOURCE_ADAPTER_RELEASE_ARCHIVE_DELIVERY_RUNTIME_NEEDS_REVIEW"

DELIVERY_TARGETS = ("evidence_queue", "total_export_package", "release_index", "archive_handoff")

@dataclass(frozen=True)
class SourceAdapterReleaseArchiveDeliveryRuntime:
    package: dict[str, Any]
    def as_dict(self) -> dict[str, Any]:
        return deepcopy(self.package)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}.{sha256_text(value)[:12]}"


def _rows(container: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    value = container.get(key) or []
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        return []
    return [dict(row) for row in value if isinstance(row, Mapping)]


def _validate_evidence_export_package(package: Mapping[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    handoff = package.get("source_adapter_evidence_export_runtime_bridge_handoff") or {}
    if not isinstance(handoff, Mapping) or handoff.get("handoff_status") != EVIDENCE_EXPORT_HANDOFF_STATUS:
        issues.append({"issue_id": "evidence_export_handoff_not_ready", "severity": "error", "message": "evidence export runtime bridge handoff was not ready"})
    expected = {
        "source_adapter_evidence_export_queue": ("evidence_export_queue_rows", 5),
        "source_adapter_total_export_source_package": ("source_total_export_rows", 5),
        "source_adapter_release_index_runtime_package": ("release_index_runtime_rows", 5),
        "source_adapter_archive_handoff_runtime_package": ("archive_handoff_runtime_rows", 5),
    }
    for key, (row_key, count) in expected.items():
        value = package.get(key) or {}
        if not isinstance(value, Mapping) or len(_rows(value, row_key)) != count:
            issues.append({"issue_id": f"unexpected_{row_key}_count", "severity": "error", "expected": count})
    return issues


def _site_rows(package: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    evidence_rows = _rows(package.get("source_adapter_evidence_export_queue") or {}, "evidence_export_queue_rows")
    return {str(row.get("named_site_id")): row for row in evidence_rows}


def _build_delivery_plan(package: Mapping[str, Any], output_root: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    sites = _site_rows(package)
    for site_id, evidence_row in sorted(sites.items()):
        for target in DELIVERY_TARGETS:
            payload = {"site": site_id, "target": target, "evidence": evidence_row.get("source_evidence_item_id")}
            rows.append({
                "schema_version": DELIVERY_PLAN_ROW_SCHEMA_VERSION,
                "row_index": len(rows),
                "release_archive_delivery_plan_row_id": stable_id("source_adapter.release_archive_delivery_plan_row", payload),
                "named_site_id": site_id,
                "adapter_id": evidence_row.get("adapter_id"),
                "source_kind": evidence_row.get("source_kind"),
                "source_evidence_item_id": evidence_row.get("source_evidence_item_id"),
                "delivery_target": target,
                "delivery_mode": "local_filesystem_delivery_runtime",
                "delivery_output_path": str(output_root / site_id / f"{target}.json"),
                "delivery_ready": True,
                "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
            })
    return {
        "schema_version": DELIVERY_PLAN_SCHEMA_VERSION,
        "release_archive_delivery_plan_status": DELIVERY_PLAN_STATUS,
        "delivery_target_count": len(DELIVERY_TARGETS),
        "delivery_plan_row_count": len(rows),
        "named_site_count": len(sites),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "release_archive_delivery_plan_rows": rows,
    }


def _payload_for_target(row: Mapping[str, Any], package: Mapping[str, Any]) -> dict[str, Any]:
    target = str(row.get("delivery_target"))
    named_site_id = str(row.get("named_site_id"))
    mapping = {
        "evidence_queue": ("source_adapter_evidence_export_queue", "evidence_export_queue_rows"),
        "total_export_package": ("source_adapter_total_export_source_package", "source_total_export_rows"),
        "release_index": ("source_adapter_release_index_runtime_package", "release_index_runtime_rows"),
        "archive_handoff": ("source_adapter_archive_handoff_runtime_package", "archive_handoff_runtime_rows"),
    }
    package_key, row_key = mapping.get(target, ("", ""))
    source_rows = _rows(package.get(package_key) or {}, row_key) if package_key else []
    source = next((r for r in source_rows if str(r.get("named_site_id")) == named_site_id), {})
    return {
        "schema_version": "source_adapter_release_archive_delivery_payload_v1",
        "delivery_target": target,
        "named_site_id": named_site_id,
        "adapter_id": row.get("adapter_id"),
        "source_kind": row.get("source_kind"),
        "source_payload": source,
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
    }


def _execute_delivery_plan(plan: Mapping[str, Any], package: Mapping[str, Any]) -> dict[str, Any]:
    receipts: list[dict[str, Any]] = []
    for row in _rows(plan, "release_archive_delivery_plan_rows"):
        path = Path(str(row.get("delivery_output_path")))
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = _payload_for_target(row, package)
        data = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(data, encoding="utf-8")
        os.replace(tmp, path)
        receipts.append({
            "schema_version": DELIVERY_RECEIPT_ROW_SCHEMA_VERSION,
            "row_index": len(receipts),
            "release_archive_delivery_receipt_row_id": stable_id("source_adapter.release_archive_delivery_receipt", {"path": str(path), "payload": payload}),
            "source_release_archive_delivery_plan_row_id": row.get("release_archive_delivery_plan_row_id"),
            "named_site_id": row.get("named_site_id"),
            "adapter_id": row.get("adapter_id"),
            "source_kind": row.get("source_kind"),
            "delivery_target": row.get("delivery_target"),
            "delivery_output_path": str(path),
            "delivery_output_exists": path.exists(),
            "delivery_output_byte_count": path.stat().st_size,
            "delivery_output_sha256": sha256_file(path),
            "delivery_execution_performed": True,
            "delivery_receipt_status": "SOURCE_ADAPTER_RELEASE_ARCHIVE_DELIVERY_RECEIPT_RECORDED",
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        })
    return {
        "schema_version": DELIVERY_RECEIPT_BATCH_SCHEMA_VERSION,
        "release_archive_delivery_receipt_batch_status": DELIVERY_RECEIPT_BATCH_STATUS,
        "delivery_receipt_row_count": len(receipts),
        "delivered_named_site_count": len({r.get("named_site_id") for r in receipts}),
        "delivery_target_count": len(DELIVERY_TARGETS),
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        "release_archive_delivery_receipt_rows": receipts,
    }


def build_source_adapter_release_archive_delivery_runtime(
    evidence_export_package: Mapping[str, Any] | None = None,
    *,
    output_dir: str | Path | None = None,
    operator_id: str = "operator",
    delivery_notes: Sequence[str] | None = None,
) -> SourceAdapterReleaseArchiveDeliveryRuntime:
    evidence_export_package = evidence_export_package or example_evidence_export_runtime_bridge_package()
    output_root = Path(output_dir) if output_dir is not None else Path(tempfile.mkdtemp(prefix="source_adapter_release_archive_delivery_"))
    issues = _validate_evidence_export_package(evidence_export_package)
    plan = _build_delivery_plan(evidence_export_package, output_root)
    receipts = _execute_delivery_plan(plan, evidence_export_package) if not issues else {
        "schema_version": DELIVERY_RECEIPT_BATCH_SCHEMA_VERSION,
        "release_archive_delivery_receipt_batch_status": "SOURCE_ADAPTER_RELEASE_ARCHIVE_DELIVERY_RECEIPTS_BLOCKED",
        "delivery_receipt_row_count": 0,
        "release_archive_delivery_receipt_rows": [],
        "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
    }
    status = STATUS if not issues else BLOCKED_STATUS
    handoff_status = HANDOFF_STATUS if not issues else BLOCKED_STATUS
    package = {
        "schema_version": SCHEMA_VERSION,
        "release_archive_delivery_runtime_status": status,
        "source_adapter_release_archive_delivery_runtime_id": stable_id("source_adapter.release_archive_delivery_runtime", {"plan": plan, "receipts": receipts, "issues": issues}),
        "operator_id": operator_id,
        "issue_count": len(issues),
        "issues": issues,
        "delivery_logic": {
            "input_source": "source_adapter_evidence_export_runtime_bridge",
            "delivery_mode": "local_filesystem_delivery_runtime",
            "delivery_execution_performed": not issues,
            "evidence_queue_outputs_written": True,
            "total_export_outputs_written": True,
            "release_index_outputs_written": True,
            "archive_handoff_outputs_written": True,
            "keys_accounts_references_preserved_redacted": True,
        },
        "source_adapter_release_archive_delivery_plan": plan,
        "source_adapter_release_archive_delivery_receipt_batch": receipts,
        "source_adapter_release_archive_delivery_runtime_handoff": {
            "schema_version": HANDOFF_SCHEMA_VERSION,
            "handoff_status": handoff_status,
            "delivery_plan_row_count": plan["delivery_plan_row_count"],
            "delivery_receipt_row_count": receipts["delivery_receipt_row_count"],
            "delivered_named_site_count": receipts.get("delivered_named_site_count", 0),
            "required_next_stage": "source_adapter_operator_delivery_receipt_closeout",
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
        },
        "operator_summary": {
            "schema_version": SUMMARY_SCHEMA_VERSION,
            "status": status,
            "operator_id": operator_id,
            "delivery_plan_row_count": plan["delivery_plan_row_count"],
            "delivery_receipt_row_count": receipts["delivery_receipt_row_count"],
            "delivered_named_site_count": receipts.get("delivered_named_site_count", 0),
            "keys_accounts_label": KEYS_ACCOUNTS_LABEL,
            "next_actions": [
                "Review release/archive delivery receipts and hashes.",
                "Promote accepted delivery receipts into final operator closeout.",
                "Use delivery artifacts as the source for evidence queue, Total Export, release index, and archive handoff outputs.",
            ],
        },
    }
    return SourceAdapterReleaseArchiveDeliveryRuntime(package)


def example_release_archive_delivery_runtime_package() -> dict[str, Any]:
    return build_source_adapter_release_archive_delivery_runtime(delivery_notes=["example release archive delivery runtime"]).as_dict()


def main() -> None:
    print(json.dumps(example_release_archive_delivery_runtime_package(), indent=2, sort_keys=True, ensure_ascii=False))

if __name__ == "__main__":
    main()
