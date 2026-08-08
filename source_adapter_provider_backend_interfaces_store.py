from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from source_adapter_provider_backend_interfaces import SCHEMA_VERSION, build_source_adapter_provider_backend_interfaces
from source_adapter_provider_backend_interfaces_verifier import verify_source_adapter_provider_backend_interfaces

STORE_SCHEMA_VERSION = "source_adapter_provider_backend_interfaces_store_v1"


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"


def _write_json(path: Path, value: Any) -> dict[str, Any]:
    data = _json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {"role": path.stem.split(".")[-1], "filename": path.name, "path": str(path), "byte_count": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def store_source_adapter_provider_backend_interfaces(package_or_runtime: Mapping[str, Any], output_dir: str | Path) -> dict[str, Any]:
    if package_or_runtime.get("schema_version") == SCHEMA_VERSION:
        package = dict(package_or_runtime)
    else:
        package = build_source_adapter_provider_backend_interfaces(package_or_runtime, output_dir=output_dir).as_dict()
    output_path = Path(output_dir)
    package_id = str(package["source_adapter_provider_backend_interfaces_id"])
    artifacts = [
        ("source_adapter_provider_backend_interfaces_package", package),
        ("source_adapter_provider_backend_registry", package["source_adapter_provider_backend_registry"]),
        ("source_adapter_provider_backend_request_matrix", package["source_adapter_provider_backend_request_matrix"]),
        ("source_adapter_provider_backend_execution_receipt_batch", package["source_adapter_provider_backend_execution_receipt_batch"]),
        ("source_adapter_provider_backend_interfaces_handoff", package["source_adapter_provider_backend_interfaces_handoff"]),
        ("source_adapter_provider_backend_interfaces_operator_summary", package["operator_summary"]),
    ]
    stored_files = [_write_json(output_path / f"{package_id}.{role}.json", payload) for role, payload in artifacts]
    verification = verify_source_adapter_provider_backend_interfaces(package)
    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "store_status": "STORED",
        "source_adapter_provider_backend_interfaces_id": package_id,
        "provider_backend_interfaces_status": package.get("provider_backend_interfaces_status"),
        "provider_backend_row_count": package["source_adapter_provider_backend_registry"].get("provider_backend_row_count", 0),
        "provider_backend_request_row_count": package["source_adapter_provider_backend_request_matrix"].get("provider_backend_request_row_count", 0),
        "provider_backend_execution_receipt_row_count": package["source_adapter_provider_backend_execution_receipt_batch"].get("provider_backend_execution_receipt_row_count", 0),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
        "verification": verification,
    }
