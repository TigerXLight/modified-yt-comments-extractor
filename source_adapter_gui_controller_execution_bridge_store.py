from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from source_adapter_gui_controller_execution_bridge import SCHEMA_VERSION, build_source_adapter_gui_controller_execution_bridge
from source_adapter_gui_controller_execution_bridge_verifier import verify_source_adapter_gui_controller_execution_bridge

STORE_SCHEMA_VERSION = "source_adapter_gui_controller_execution_bridge_store_v1"


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"


def _write_json(path: Path, value: Any) -> dict[str, Any]:
    data = _json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {"role": path.stem.split(".")[-1], "filename": path.name, "path": str(path), "byte_count": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def store_source_adapter_gui_controller_execution_bridge(package_or_runtime: Mapping[str, Any], output_dir: str | Path) -> dict[str, Any]:
    if package_or_runtime.get("schema_version") == SCHEMA_VERSION:
        package = dict(package_or_runtime)
    else:
        package = build_source_adapter_gui_controller_execution_bridge(package_or_runtime, output_dir=output_dir).as_dict()
    output_path = Path(output_dir)
    bridge_id = str(package["source_adapter_gui_controller_execution_bridge_id"])
    artifacts = [
        ("source_adapter_gui_controller_execution_bridge_package", package),
        ("source_adapter_gui_controller_execution_route_registry", package["source_adapter_gui_controller_execution_route_registry"]),
        ("source_adapter_gui_controller_execution_dispatch_receipt_batch", package["source_adapter_gui_controller_execution_dispatch_receipt_batch"]),
        ("source_adapter_gui_controller_execution_bridge_handoff", package["source_adapter_gui_controller_execution_bridge_handoff"]),
        ("source_adapter_gui_controller_execution_bridge_operator_summary", package["operator_summary"]),
    ]
    stored_files = [_write_json(output_path / f"{bridge_id}.{role}.json", payload) for role, payload in artifacts]
    verification = verify_source_adapter_gui_controller_execution_bridge(package)
    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "store_status": "STORED",
        "source_adapter_gui_controller_execution_bridge_id": bridge_id,
        "gui_controller_execution_bridge_status": package.get("gui_controller_execution_bridge_status"),
        "route_row_count": package["source_adapter_gui_controller_execution_route_registry"].get("route_row_count", 0),
        "dispatch_receipt_row_count": package["source_adapter_gui_controller_execution_dispatch_receipt_batch"].get("dispatch_receipt_row_count", 0),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
        "verification": verification,
    }
