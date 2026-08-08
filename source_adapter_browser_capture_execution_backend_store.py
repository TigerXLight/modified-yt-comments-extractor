from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

from source_adapter_browser_capture_execution_backend import example_browser_capture_execution_backend_package

SCHEMA_VERSION = "source_adapter_browser_capture_execution_backend_store_v1"
STORE_STATUS = "STORED"

ROLES = {
    "package": lambda p: p,
    "handoff": lambda p: p["handoff"],
    "operator_summary": lambda p: p["operator_summary"],
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


def store_source_adapter_browser_capture_execution_backend_package(package: Mapping[str, Any] | None = None, output_dir: str | Path | None = None) -> dict[str, Any]:
    package = dict(package or example_browser_capture_execution_backend_package())
    output_root = Path(output_dir) if output_dir is not None else Path(tempfile.mkdtemp(prefix="source_adapter_browser_capture_execution_backend_store_"))
    package_id = str(package["id"])
    stored_files = []
    for role, getter in ROLES.items():
        path = output_root / f"{package_id}.{role}.json"
        meta = _atomic_write_json(path, getter(package))
        meta["role"] = role
        stored_files.append(meta)
    return {
        "schema_version": SCHEMA_VERSION,
        "store_status": STORE_STATUS,
        "id": package_id,
        "status": package.get("status"),
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
    }


if __name__ == "__main__":
    print(json.dumps(store_source_adapter_browser_capture_execution_backend_package(), indent=2, sort_keys=True))
