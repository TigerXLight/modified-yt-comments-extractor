from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

from source_adapter_evidence_export_runtime_bridge import STATUS, example_evidence_export_runtime_bridge_package

SCHEMA_VERSION = "source_adapter_evidence_export_runtime_bridge_store_v1"
STORE_STATUS = "STORED"

ROLES = {
    "source_adapter_evidence_export_runtime_bridge_package": lambda p: p,
    "source_adapter_evidence_export_queue": lambda p: p["source_adapter_evidence_export_queue"],
    "source_adapter_total_export_source_package": lambda p: p["source_adapter_total_export_source_package"],
    "source_adapter_release_index_runtime_package": lambda p: p["source_adapter_release_index_runtime_package"],
    "source_adapter_archive_handoff_runtime_package": lambda p: p["source_adapter_archive_handoff_runtime_package"],
    "source_adapter_evidence_export_runtime_bridge_handoff": lambda p: p["source_adapter_evidence_export_runtime_bridge_handoff"],
    "source_adapter_evidence_export_runtime_bridge_operator_summary": lambda p: p["operator_summary"],
}

def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _atomic_write_json(path: Path, value: Any) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
    os.replace(tmp_name, path)
    return {"path": str(path), "filename": path.name, "byte_count": len(data), "sha256": _sha256_bytes(data)}

def store_source_adapter_evidence_export_runtime_bridge_package(package: Mapping[str, Any] | None = None, output_dir: str | Path | None = None) -> dict[str, Any]:
    package = dict(package or example_evidence_export_runtime_bridge_package())
    output_root = Path(output_dir) if output_dir is not None else Path(tempfile.mkdtemp(prefix="source_adapter_evidence_export_runtime_bridge_store_"))
    package_id = str(package["source_adapter_evidence_export_runtime_bridge_id"])
    stored_files = []
    for role, getter in ROLES.items():
        path = output_root / f"{package_id}.{role}.json"
        meta = _atomic_write_json(path, getter(package))
        meta["role"] = role
        stored_files.append(meta)
    return {
        "schema_version": SCHEMA_VERSION,
        "store_status": STORE_STATUS,
        "source_adapter_evidence_export_runtime_bridge_id": package_id,
        "evidence_export_runtime_bridge_status": package.get("evidence_export_runtime_bridge_status"),
        "evidence_export_queue_row_count": package["source_adapter_evidence_export_queue"]["evidence_export_queue_row_count"],
        "total_export_source_row_count": package["source_adapter_total_export_source_package"]["total_export_source_row_count"],
        "release_index_runtime_row_count": package["source_adapter_release_index_runtime_package"]["release_index_runtime_row_count"],
        "archive_handoff_runtime_row_count": package["source_adapter_archive_handoff_runtime_package"]["archive_handoff_runtime_row_count"],
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
    }

if __name__ == "__main__":
    print(json.dumps(store_source_adapter_evidence_export_runtime_bridge_package(), indent=2, sort_keys=True))
