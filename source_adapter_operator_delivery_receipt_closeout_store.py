from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

from source_adapter_operator_delivery_receipt_closeout import example_operator_delivery_receipt_closeout_package

SCHEMA_VERSION = "source_adapter_operator_delivery_receipt_closeout_store_v1"
STORE_STATUS = "STORED"
ROLES = {
    "source_adapter_operator_delivery_receipt_closeout_package": lambda p: p,
    "source_adapter_operator_delivery_receipt_review": lambda p: p["source_adapter_operator_delivery_receipt_review"],
    "source_adapter_operator_delivery_acceptance_matrix": lambda p: p["source_adapter_operator_delivery_acceptance_matrix"],
    "source_adapter_operator_delivery_release_gate": lambda p: p["source_adapter_operator_delivery_release_gate"],
    "source_adapter_operator_delivery_receipt_closeout_handoff": lambda p: p["source_adapter_operator_delivery_receipt_closeout_handoff"],
    "source_adapter_operator_delivery_receipt_closeout_summary": lambda p: p["operator_summary"],
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

def store_source_adapter_operator_delivery_receipt_closeout_package(package: Mapping[str, Any] | None = None, output_dir: str | Path | None = None) -> dict[str, Any]:
    package = dict(package or example_operator_delivery_receipt_closeout_package())
    output_root = Path(output_dir) if output_dir is not None else Path(tempfile.mkdtemp(prefix="source_adapter_operator_delivery_receipt_closeout_store_"))
    package_id = str(package["source_adapter_operator_delivery_receipt_closeout_id"])
    stored_files = []
    for role, getter in ROLES.items():
        path = output_root / f"{package_id}.{role}.json"
        meta = _atomic_write_json(path, getter(package))
        meta["role"] = role
        stored_files.append(meta)
    review = package["source_adapter_operator_delivery_receipt_review"]
    acceptance = package["source_adapter_operator_delivery_acceptance_matrix"]
    return {
        "schema_version": SCHEMA_VERSION,
        "store_status": STORE_STATUS,
        "source_adapter_operator_delivery_receipt_closeout_id": package_id,
        "operator_delivery_receipt_closeout_status": package.get("operator_delivery_receipt_closeout_status"),
        "operator_delivery_receipt_review_row_count": review["operator_delivery_receipt_review_row_count"],
        "operator_delivery_acceptance_row_count": acceptance["operator_delivery_acceptance_row_count"],
        "release_section_completion_ready": package["source_adapter_operator_delivery_release_gate"]["release_section_completion_ready"],
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
    }

if __name__ == "__main__":
    print(json.dumps(store_source_adapter_operator_delivery_receipt_closeout_package(), indent=2, sort_keys=True))
