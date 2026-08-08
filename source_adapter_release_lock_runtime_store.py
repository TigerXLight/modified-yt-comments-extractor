from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

from source_adapter_release_lock_runtime import example_source_adapter_release_lock_runtime_package

SCHEMA_VERSION = "source_adapter_release_lock_runtime_store_v1"
STORE_STATUS = "STORED"
ROLES = {"package": lambda p: p, "handoff": lambda p: p["handoff"], "operator_summary": lambda p: p["operator_summary"]}


def _atomic_write_json(path: Path, value: Any) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
    os.replace(tmp_name, path)
    return {"path": str(path), "filename": path.name, "byte_count": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def store_source_adapter_release_lock_runtime_package(package: Mapping[str, Any] | None = None, output_dir: str | Path | None = None) -> dict[str, Any]:
    package = dict(package or example_source_adapter_release_lock_runtime_package())
    output_root = Path(output_dir) if output_dir is not None else Path(tempfile.mkdtemp(prefix="source_adapter_release_lock_runtime_store_"))
    stored_files = []
    for role, getter in ROLES.items():
        meta = _atomic_write_json(output_root / f"{package['id']}.{role}.json", getter(package))
        meta["role"] = role
        stored_files.append(meta)
    return {"schema_version": SCHEMA_VERSION, "store_status": STORE_STATUS, "id": package["id"], "status": package["status"], "output_file_count": len(stored_files), "stored_files": stored_files}

if __name__ == "__main__":
    print(json.dumps(store_source_adapter_release_lock_runtime_package(), indent=2, sort_keys=True))
