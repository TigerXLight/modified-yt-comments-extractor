from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

from source_adapter_registry_release import build_source_adapter_registry_release, load_json, write_json_file
from source_adapter_registry_release_verifier import verify_source_adapter_registry_release

STORE_SCHEMA_VERSION = "source_adapter_registry_release_store_v1"


def _json_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stored_file(path: Path, role: str) -> dict[str, Any]:
    return {
        "role": role,
        "filename": path.name,
        "byte_count": path.stat().st_size,
        "sha256": _json_hash(path),
    }


def store_source_adapter_registry_release(
    adapter_registry_update_package: Mapping[str, Any],
    output_dir: str | Path,
) -> dict[str, Any]:
    package = build_source_adapter_registry_release(adapter_registry_update_package)
    verification = verify_source_adapter_registry_release(package)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    release_id = package["source_adapter_registry_release_id"]
    outputs = [
        ("source_adapter_registry_release_package", package),
        ("source_adapter_registry_release_record", package["adapter_registry_release_record"]),
        ("source_adapter_frozen_registry", package["source_adapter_frozen_registry"]),
        ("source_adapter_registry_rollout_handoff", package["source_adapter_registry_rollout_handoff"]),
        ("source_adapter_registry_release_operator_summary", package["operator_summary"]),
    ]
    stored_files: list[dict[str, Any]] = []
    for role, data in outputs:
        path = destination / f"{release_id}.{role}.json"
        write_json_file(path, data)
        stored_files.append(_stored_file(path, role))
    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "source_adapter_registry_release_id": release_id,
        "source_adapter_registry_update_id": package["source_adapter_registry_update_id"],
        "source_adapter_coverage_acceptance_id": package["source_adapter_coverage_acceptance_id"],
        "registry_release_status": package["registry_release_status"],
        "adapter_count": package["adapter_count"],
        "output_file_count": len(stored_files),
        "store_status": "STORED",
        "stored_files": stored_files,
        "verification": verification,
    }


def store_source_adapter_registry_release_from_files(
    adapter_registry_update_package_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    package = load_json(adapter_registry_update_package_path)
    return store_source_adapter_registry_release(package, output_dir)


if __name__ == "__main__":
    from tempfile import TemporaryDirectory
    from source_adapter_registry_release_test import _registry_update_package

    with TemporaryDirectory() as tmp:
        summary = store_source_adapter_registry_release(_registry_update_package(), tmp)
        assert summary["output_file_count"] == 5, summary
        assert summary["verification"]["verified"] is True, summary
    print("Source Adapter Registry Release store self-test passed.")
