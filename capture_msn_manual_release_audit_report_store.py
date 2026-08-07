from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from capture_msn_manual_release_audit_report import msn_manual_release_audit_report_to_json

SCHEMA_VERSION = "msn_manual_release_audit_report_store_v1"


def _write_json(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    data = (json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    path.write_bytes(data)
    return {
        "filename": path.name,
        "role": str(payload.get("role") or path.stem.rsplit(".", 1)[-1]),
        "sha256": hashlib.sha256(data).hexdigest(),
        "byte_count": len(data),
    }


def store_msn_manual_release_audit_report(
    packet: Mapping[str, Any],
    output_dir: str | Path,
) -> dict[str, Any]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    audit_id = str(packet.get("audit_report_id") or "msn_manual_release.audit")
    report_path = out_dir / f"{audit_id}.release_audit_report.json"
    ledger_path = out_dir / f"{audit_id}.release_audit_artifact_ledger.json"
    trace_path = out_dir / f"{audit_id}.release_audit_traceability_map.json"
    receipt_path = out_dir / f"{audit_id}.release_audit_operator_receipt.json"

    report_data = msn_manual_release_audit_report_to_json(packet).encode("utf-8")
    report_path.write_bytes(report_data)
    report_file = {
        "filename": report_path.name,
        "role": "msn_manual_release_audit_report",
        "sha256": hashlib.sha256(report_data).hexdigest(),
        "byte_count": len(report_data),
    }

    ledger_file = _write_json(
        ledger_path,
        {
            "role": "msn_manual_release_audit_artifact_ledger",
            "schema_version": "msn_manual_release_audit_artifact_ledger_v1",
            "audit_report_id": packet.get("audit_report_id"),
            "queue_item_id": packet.get("queue_item_id"),
            "release_id": packet.get("release_id"),
            "artifact_quality": packet.get("artifact_quality", {}),
            "artifact_ledger": packet.get("artifact_ledger", []),
        },
    )
    trace_file = _write_json(
        trace_path,
        {
            "role": "msn_manual_release_audit_traceability_map",
            "schema_version": "msn_manual_release_audit_traceability_map_v1",
            "audit_report_id": packet.get("audit_report_id"),
            "pipeline_closeout_id": packet.get("pipeline_closeout_id"),
            "queue_item_id": packet.get("queue_item_id"),
            "release_id": packet.get("release_id"),
            "stage_coverage": packet.get("stage_coverage", {}),
            "transition_map": packet.get("transition_map", {}),
            "readiness_issues": packet.get("readiness_issues", []),
        },
    )
    receipt_file = _write_json(
        receipt_path,
        {
            "role": "msn_manual_release_audit_operator_receipt",
            "schema_version": "msn_manual_release_audit_operator_receipt_v1",
            "audit_report_id": packet.get("audit_report_id"),
            "audit_status": packet.get("audit_status"),
            "operator_label": packet.get("operator_label"),
            "operator_constraints": packet.get("operator_constraints", []),
            "release_claims": packet.get("release_claims", []),
        },
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "store_status": "STORED",
        "audit_report_id": packet.get("audit_report_id"),
        "queue_item_id": packet.get("queue_item_id"),
        "release_id": packet.get("release_id"),
        "output_file_count": 4,
        "stored_files": [report_file, ledger_file, trace_file, receipt_file],
    }


if __name__ == "__main__":
    import tempfile
    from capture_msn_manual_release_audit_report import build_msn_manual_release_audit_report, _REQUIRED_STAGE_KEYS

    packet = build_msn_manual_release_audit_report(
        {
            "schema_version": "msn_manual_release_pipeline_closeout_v1",
            "pipeline_status": "MSN_MANUAL_RELEASE_PIPELINE_CLOSED",
            "queue_item_id": "msn.queue",
            "release_id": "msn.queue.release.1234",
            "pipeline_closeout_id": "msn.queue.release.1234.pipeline_closeout.abc123",
            "transition_map": {"to_status": "TOTAL_EXPORT_RELEASE_READY_FOR_OPERATOR_ARCHIVAL"},
            "stage_coverage": {key: True for key in _REQUIRED_STAGE_KEYS},
            "stored_files": [
                {"filename": "a.json", "role": "test", "sha256": "1" * 64, "byte_count": 1},
            ],
        }
    )
    with tempfile.TemporaryDirectory() as tmp:
        result = store_msn_manual_release_audit_report(packet, tmp)
        assert result["store_status"] == "STORED"
        assert result["output_file_count"] == 4
    print("MSN manual release audit report store self-test passed.")
