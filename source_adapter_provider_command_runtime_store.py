from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping

from source_adapter_provider_command_runtime import example_provider_command_runtime_package
from source_adapter_provider_command_runtime_verifier import verify_source_adapter_provider_command_runtime_package

STORE_SCHEMA_VERSION = "source_adapter_provider_command_runtime_store_v1"


def _write_json(path: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    data = path.read_bytes()
    return {"path": str(path), "filename": path.name, "byte_count": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def store_source_adapter_provider_command_runtime_package(package: Mapping[str, Any] | None = None, output_dir: str | Path | None = None) -> dict[str, Any]:
    package = dict(package or example_provider_command_runtime_package())
    output = Path(output_dir) if output_dir is not None else Path(tempfile.mkdtemp(prefix="source_adapter_provider_command_runtime_store_"))
    package_id = str(package.get("source_adapter_provider_command_runtime_id") or "source_adapter.provider_command_runtime.unknown")
    artifacts = []
    artifacts.append({"role": "source_adapter_provider_command_runtime_package", **_write_json(output / f"{package_id}.provider_command_runtime_package.json", package)})
    artifacts.append({"role": "source_adapter_provider_command_request_matrix", **_write_json(output / f"{package_id}.provider_command_request_matrix.json", package.get("source_adapter_provider_command_request_matrix") or {})})
    artifacts.append({"role": "source_adapter_provider_command_execution_receipt_batch", **_write_json(output / f"{package_id}.provider_command_execution_receipt_batch.json", package.get("source_adapter_provider_command_execution_receipt_batch") or {})})
    artifacts.append({"role": "source_adapter_provider_command_runtime_handoff", **_write_json(output / f"{package_id}.provider_command_runtime_handoff.json", package.get("source_adapter_provider_command_runtime_handoff") or {})})
    artifacts.append({"role": "source_adapter_provider_command_runtime_operator_summary", **_write_json(output / f"{package_id}.provider_command_runtime_operator_summary.json", package.get("operator_summary") or {})})
    verification = verify_source_adapter_provider_command_runtime_package(package)
    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "store_status": "STORED",
        "source_adapter_provider_command_runtime_id": package_id,
        "provider_command_runtime_status": package.get("provider_command_runtime_status"),
        "provider_command_request_row_count": package.get("source_adapter_provider_command_request_matrix", {}).get("provider_command_request_row_count", 0),
        "provider_command_execution_receipt_row_count": package.get("source_adapter_provider_command_execution_receipt_batch", {}).get("provider_command_execution_receipt_row_count", 0),
        "output_file_count": len(artifacts),
        "stored_files": artifacts,
        "verification": verification,
    }


if __name__ == "__main__":
    print(json.dumps(store_source_adapter_provider_command_runtime_package(), indent=2, sort_keys=True))
