from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from source_adapter_priority_fixture_pack_implementation import (
    SCHEMA_VERSION,
    build_source_adapter_priority_fixture_pack_implementation,
)
from source_adapter_priority_fixture_pack_implementation_verifier import verify_source_adapter_priority_fixture_pack_implementation

STORE_SCHEMA_VERSION = "source_adapter_priority_fixture_pack_implementation_store_v1"


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


def store_source_adapter_priority_fixture_pack_implementation(package_or_runtime_gui_provider_implementation: Mapping[str, Any], output_dir: str | Path) -> dict[str, Any]:
    if package_or_runtime_gui_provider_implementation.get("schema_version") == SCHEMA_VERSION:
        package = dict(package_or_runtime_gui_provider_implementation)
    else:
        package = build_source_adapter_priority_fixture_pack_implementation(package_or_runtime_gui_provider_implementation).as_dict()
    output_path = Path(output_dir)
    implementation_id = str(package["source_adapter_priority_fixture_pack_implementation_id"])
    artifacts = [
        ("source_adapter_priority_fixture_pack_implementation_package", package),
        ("source_adapter_priority_fixture_pack_catalog", package["source_adapter_priority_fixture_pack_catalog"]),
        ("source_adapter_priority_fixture_pack_execution_matrix", package["source_adapter_priority_fixture_pack_execution_matrix"]),
        ("source_adapter_priority_fixture_pack_dispatch_receipt_batch", package["source_adapter_priority_fixture_pack_dispatch_receipt_batch"]),
        ("source_adapter_priority_fixture_pack_gui_installation_checklist", package["source_adapter_priority_fixture_pack_gui_installation_checklist"]),
        ("source_adapter_priority_fixture_pack_named_site_smoke_queue", package["source_adapter_priority_fixture_pack_named_site_smoke_queue"]),
        ("source_adapter_priority_fixture_pack_implementation_handoff", package["source_adapter_priority_fixture_pack_implementation_handoff"]),
        ("source_adapter_priority_fixture_pack_implementation_operator_summary", package["operator_summary"]),
    ]
    stored_files = [_write_json(output_path / f"{implementation_id}.{role}.json", payload) for role, payload in artifacts]
    verification = verify_source_adapter_priority_fixture_pack_implementation(package)
    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "store_status": "STORED",
        "source_adapter_priority_fixture_pack_implementation_id": implementation_id,
        "priority_fixture_pack_implementation_status": package.get("priority_fixture_pack_implementation_status"),
        "fixture_pack_count": package["source_adapter_priority_fixture_pack_catalog"].get("fixture_pack_count", 0),
        "fixture_pack_execution_row_count": package["source_adapter_priority_fixture_pack_execution_matrix"].get("fixture_pack_execution_row_count", 0),
        "dispatch_receipt_count": package["source_adapter_priority_fixture_pack_dispatch_receipt_batch"].get("fixture_pack_dispatch_receipt_count", 0),
        "named_site_smoke_queue_count": package["source_adapter_priority_fixture_pack_named_site_smoke_queue"].get("named_site_smoke_queue_count", 0),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
        "verification": verification,
    }
