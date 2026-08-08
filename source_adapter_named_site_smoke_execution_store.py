from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping

from source_adapter_named_site_smoke_execution import example_named_site_smoke_execution_package
from source_adapter_named_site_smoke_execution_verifier import verify_source_adapter_named_site_smoke_execution_package

STORE_SCHEMA_VERSION = "source_adapter_named_site_smoke_execution_store_v1"


def _write_json(path: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    data = path.read_bytes()
    return {"path": str(path), "filename": path.name, "byte_count": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def store_source_adapter_named_site_smoke_execution_package(package: Mapping[str, Any] | None = None, output_dir: str | Path | None = None) -> dict[str, Any]:
    package = dict(package or example_named_site_smoke_execution_package())
    output = Path(output_dir) if output_dir is not None else Path(tempfile.mkdtemp(prefix="source_adapter_named_site_smoke_execution_store_"))
    package_id = str(package.get("source_adapter_named_site_smoke_execution_id") or "source_adapter.named_site_smoke_execution.unknown")
    artifacts = []
    artifacts.append({"role": "source_adapter_named_site_smoke_execution_package", **_write_json(output / f"{package_id}.named_site_smoke_execution_package.json", package)})
    artifacts.append({"role": "source_adapter_named_site_smoke_execution_matrix", **_write_json(output / f"{package_id}.named_site_smoke_execution_matrix.json", package.get("source_adapter_named_site_smoke_execution_matrix") or {})})
    artifacts.append({"role": "source_adapter_named_site_provider_action_receipts", **_write_json(output / f"{package_id}.named_site_provider_action_receipts.json", package.get("source_adapter_named_site_provider_action_receipt_batch") or {})})
    artifacts.append({"role": "source_adapter_named_site_smoke_execution_manifest", **_write_json(output / f"{package_id}.named_site_smoke_execution_manifest.json", package.get("source_adapter_named_site_smoke_execution_manifest") or {})})
    artifacts.append({"role": "source_adapter_named_site_smoke_execution_handoff", **_write_json(output / f"{package_id}.named_site_smoke_execution_handoff.json", package.get("source_adapter_named_site_smoke_execution_handoff") or {})})
    verification = verify_source_adapter_named_site_smoke_execution_package(package)
    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "store_status": "STORED",
        "source_adapter_named_site_smoke_execution_id": package_id,
        "named_site_smoke_execution_status": package.get("named_site_smoke_execution_status"),
        "named_site_execution_site_count": package.get("source_adapter_named_site_smoke_execution_matrix", {}).get("named_site_execution_site_count", 0),
        "named_site_provider_action_receipt_row_count": package.get("source_adapter_named_site_provider_action_receipt_batch", {}).get("named_site_provider_action_receipt_row_count", 0),
        "output_file_count": len(artifacts),
        "stored_files": artifacts,
        "verification": verification,
    }


if __name__ == "__main__":
    print(json.dumps(store_source_adapter_named_site_smoke_execution_package(), indent=2, sort_keys=True))
