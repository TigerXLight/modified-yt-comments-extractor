from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

from source_adapter_release_archive_delivery_runtime import example_release_archive_delivery_runtime_package

SCHEMA_VERSION = "source_adapter_release_archive_delivery_runtime_store_v1"
STORE_STATUS = "STORED"
ROLES = {
    "source_adapter_release_archive_delivery_runtime_package": lambda p: p,
    "source_adapter_release_archive_delivery_plan": lambda p: p["source_adapter_release_archive_delivery_plan"],
    "source_adapter_release_archive_delivery_receipt_batch": lambda p: p["source_adapter_release_archive_delivery_receipt_batch"],
    "source_adapter_release_archive_delivery_runtime_handoff": lambda p: p["source_adapter_release_archive_delivery_runtime_handoff"],
    "source_adapter_release_archive_delivery_runtime_operator_summary": lambda p: p["operator_summary"],
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

def store_source_adapter_release_archive_delivery_runtime_package(package: Mapping[str, Any] | None = None, output_dir: str | Path | None = None) -> dict[str, Any]:
    package = dict(package or example_release_archive_delivery_runtime_package())
    output_root = Path(output_dir) if output_dir is not None else Path(tempfile.mkdtemp(prefix="source_adapter_release_archive_delivery_runtime_store_"))
    package_id = str(package["source_adapter_release_archive_delivery_runtime_id"])
    stored_files = []
    for role, getter in ROLES.items():
        path = output_root / f"{package_id}.{role}.json"
        meta = _atomic_write_json(path, getter(package))
        meta["role"] = role
        stored_files.append(meta)
    receipts = package["source_adapter_release_archive_delivery_receipt_batch"]
    return {
        "schema_version": SCHEMA_VERSION,
        "store_status": STORE_STATUS,
        "source_adapter_release_archive_delivery_runtime_id": package_id,
        "release_archive_delivery_runtime_status": package.get("release_archive_delivery_runtime_status"),
        "delivery_plan_row_count": package["source_adapter_release_archive_delivery_plan"]["delivery_plan_row_count"],
        "delivery_receipt_row_count": receipts["delivery_receipt_row_count"],
        "delivered_named_site_count": receipts.get("delivered_named_site_count", 0),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
    }

if __name__ == "__main__":
    print(json.dumps(store_source_adapter_release_archive_delivery_runtime_package(), indent=2, sort_keys=True))
