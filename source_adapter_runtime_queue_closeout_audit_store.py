from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from source_adapter_runtime_queue_closeout_audit import (
    SCHEMA_VERSION,
    build_source_adapter_runtime_queue_closeout_audit,
)
from source_adapter_runtime_queue_closeout_audit_verifier import verify_source_adapter_runtime_queue_closeout_audit

STORE_SCHEMA_VERSION = "source_adapter_runtime_queue_closeout_audit_store_v1"


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


def store_source_adapter_runtime_queue_closeout_audit(package_or_runtime_wiring: Mapping[str, Any], output_dir: str | Path) -> dict[str, Any]:
    if package_or_runtime_wiring.get("schema_version") == SCHEMA_VERSION:
        package = dict(package_or_runtime_wiring)
    else:
        package = build_source_adapter_runtime_queue_closeout_audit(package_or_runtime_wiring).as_dict()
    output_path = Path(output_dir)
    closeout_id = str(package["source_adapter_runtime_queue_closeout_audit_id"])
    artifacts = [
        ("source_adapter_runtime_queue_closeout_audit_package", package),
        ("source_adapter_runtime_queue_closeout_coverage_matrix", package["source_adapter_runtime_queue_closeout_coverage_matrix"]),
        ("source_adapter_runtime_queue_closeout_roadmap_state", package["source_adapter_runtime_queue_closeout_roadmap_state"]),
        ("source_adapter_runtime_queue_closeout_release_gate", package["source_adapter_runtime_queue_closeout_release_gate"]),
        ("source_adapter_runtime_queue_closeout_operator_handoff", package["source_adapter_runtime_queue_closeout_operator_handoff"]),
        ("source_adapter_runtime_queue_closeout_operator_summary", package["operator_summary"]),
    ]
    stored_files = [_write_json(output_path / f"{closeout_id}.{role}.json", payload) for role, payload in artifacts]
    verification = verify_source_adapter_runtime_queue_closeout_audit(package)
    coverage = package["source_adapter_runtime_queue_closeout_coverage_matrix"]
    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "store_status": "STORED",
        "source_adapter_runtime_queue_closeout_audit_id": closeout_id,
        "runtime_queue_closeout_audit_status": package.get("runtime_queue_closeout_audit_status"),
        "coverage_row_count": coverage.get("coverage_row_count", 0),
        "local_runner_queue_row_count": coverage.get("local_runner_queue_row_count", 0),
        "expanded_binding_row_count": coverage.get("expanded_binding_row_count", 0),
        "acceptance_receipt_row_count": coverage.get("acceptance_receipt_row_count", 0),
        "named_site_smoke_gate_row_count": coverage.get("named_site_smoke_gate_row_count", 0),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
        "verification": verification,
    }
