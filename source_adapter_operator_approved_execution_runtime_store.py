from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from source_adapter_operator_approved_execution_runtime import (
    SCHEMA_VERSION,
    build_source_adapter_operator_approved_execution_runtime,
)
from source_adapter_operator_approved_execution_runtime_verifier import verify_source_adapter_operator_approved_execution_runtime

STORE_SCHEMA_VERSION = "source_adapter_operator_approved_execution_runtime_store_v1"


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"


def _write_json(path: Path, value: Any) -> dict[str, Any]:
    data = _json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {
        "role": path.stem.split(".")[-1],
        "filename": path.name,
        "path": str(path),
        "byte_count": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def store_source_adapter_operator_approved_execution_runtime(package_or_closeout: Mapping[str, Any], output_dir: str | Path) -> dict[str, Any]:
    if package_or_closeout.get("schema_version") == SCHEMA_VERSION:
        package = dict(package_or_closeout)
    else:
        package = build_source_adapter_operator_approved_execution_runtime(package_or_closeout, output_dir=output_dir).as_dict()
    output_path = Path(output_dir)
    runtime_id = str(package["source_adapter_operator_approved_execution_runtime_id"])
    artifacts = [
        ("source_adapter_operator_approved_execution_runtime_package", package),
        ("source_adapter_operator_approval_packet", package["source_adapter_operator_approval_packet"]),
        ("source_adapter_operator_approved_execution_queue", package["source_adapter_operator_approved_execution_queue"]),
        ("source_adapter_operator_approved_execution_rows", package["source_adapter_operator_approved_execution_rows"]),
        ("source_adapter_provider_execution_receipt_batch", package["source_adapter_provider_execution_receipt_batch"]),
        ("source_adapter_redacted_credential_reference_ledger", package["source_adapter_redacted_credential_reference_ledger"]),
        ("source_adapter_operator_approved_execution_runtime_handoff", package["source_adapter_operator_approved_execution_runtime_handoff"]),
        ("source_adapter_operator_approved_execution_runtime_operator_summary", package["operator_summary"]),
    ]
    stored_files = [_write_json(output_path / f"{runtime_id}.{role}.json", payload) for role, payload in artifacts]
    verification = verify_source_adapter_operator_approved_execution_runtime(package)
    receipt_batch = package["source_adapter_provider_execution_receipt_batch"]
    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "store_status": "STORED",
        "source_adapter_operator_approved_execution_runtime_id": runtime_id,
        "operator_approved_execution_runtime_status": package.get("operator_approved_execution_runtime_status"),
        "approval_packet_row_count": package["source_adapter_operator_approval_packet"].get("approval_packet_row_count", 0),
        "execution_queue_row_count": package["source_adapter_operator_approved_execution_queue"].get("execution_queue_row_count", 0),
        "executed_row_count": len(package["source_adapter_operator_approved_execution_rows"]),
        "provider_receipt_row_count": receipt_batch.get("provider_receipt_row_count", 0),
        "credential_reference_ledger_row_count": package["source_adapter_redacted_credential_reference_ledger"].get("credential_reference_ledger_row_count", 0),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
        "verification": verification,
    }
