from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from source_adapter_runtime_gui_provider_implementation import (
    SCHEMA_VERSION,
    build_source_adapter_runtime_gui_provider_implementation,
)
from source_adapter_runtime_gui_provider_implementation_verifier import verify_source_adapter_runtime_gui_provider_implementation

STORE_SCHEMA_VERSION = "source_adapter_runtime_gui_provider_implementation_store_v1"


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


def store_source_adapter_runtime_gui_provider_implementation(package_or_work_order_closeout: Mapping[str, Any], output_dir: str | Path) -> dict[str, Any]:
    if package_or_work_order_closeout.get("schema_version") == SCHEMA_VERSION:
        package = dict(package_or_work_order_closeout)
    else:
        package = build_source_adapter_runtime_gui_provider_implementation(package_or_work_order_closeout).as_dict()
    output_path = Path(output_dir)
    implementation_id = str(package["source_adapter_runtime_gui_provider_implementation_id"])
    artifacts = [
        ("source_adapter_runtime_gui_provider_implementation_package", package),
        ("source_adapter_runtime_gui_controller_route_registry", package["source_adapter_runtime_gui_controller_route_registry"]),
        ("source_adapter_runtime_provider_execution_registry", package["source_adapter_runtime_provider_execution_registry"]),
        ("source_adapter_keys_accounts_credential_reference_selector", package["source_adapter_keys_accounts_credential_reference_selector"]),
        ("source_adapter_runtime_controller_provider_binding_matrix", package["source_adapter_runtime_controller_provider_binding_matrix"]),
        ("source_adapter_runtime_dispatch_smoke_receipt_batch", package["source_adapter_runtime_dispatch_smoke_receipt_batch"]),
        ("source_adapter_runtime_gui_provider_implementation_handoff", package["source_adapter_runtime_gui_provider_implementation_handoff"]),
        ("source_adapter_runtime_gui_provider_implementation_operator_summary", package["operator_summary"]),
    ]
    stored_files = [_write_json(output_path / f"{implementation_id}.{role}.json", payload) for role, payload in artifacts]
    verification = verify_source_adapter_runtime_gui_provider_implementation(package)
    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "store_status": "STORED",
        "source_adapter_runtime_gui_provider_implementation_id": implementation_id,
        "runtime_gui_provider_implementation_status": package.get("runtime_gui_provider_implementation_status"),
        "route_count": package["source_adapter_runtime_gui_controller_route_registry"].get("route_count", 0),
        "provider_count": package["source_adapter_runtime_provider_execution_registry"].get("provider_count", 0),
        "dispatch_smoke_receipt_count": package["source_adapter_runtime_dispatch_smoke_receipt_batch"].get("dispatch_smoke_receipt_count", 0),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
        "verification": verification,
    }
