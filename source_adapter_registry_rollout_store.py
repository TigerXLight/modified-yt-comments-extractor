from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

from source_adapter_registry_rollout import build_source_adapter_registry_rollout, load_json, write_json_file
from source_adapter_registry_rollout_verifier import verify_source_adapter_registry_rollout

STORE_SCHEMA_VERSION = "source_adapter_registry_rollout_store_v1"


def _json_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stored_file(path: Path, role: str) -> dict[str, Any]:
    return {
        "role": role,
        "filename": path.name,
        "byte_count": path.stat().st_size,
        "sha256": _json_hash(path),
    }


def store_source_adapter_registry_rollout(
    registry_release_package: Mapping[str, Any],
    output_dir: str | Path,
) -> dict[str, Any]:
    package = build_source_adapter_registry_rollout(registry_release_package)
    verification = verify_source_adapter_registry_rollout(package)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    rollout_id = package["source_adapter_registry_rollout_id"]
    outputs = [
        ("source_adapter_registry_rollout_package", package),
        ("source_adapter_source_selection_wiring_plan", package["source_adapter_source_selection_wiring_plan"]),
        ("source_adapter_selection_option_index", package["source_adapter_selection_option_index"]),
        ("source_adapter_registry_rollout_app_handoff", package["source_adapter_registry_rollout_app_handoff"]),
        ("source_adapter_registry_rollout_operator_summary", package["operator_summary"]),
    ]
    stored_files: list[dict[str, Any]] = []
    for role, data in outputs:
        path = destination / f"{rollout_id}.{role}.json"
        write_json_file(path, data)
        stored_files.append(_stored_file(path, role))
    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "source_adapter_registry_rollout_id": rollout_id,
        "source_adapter_registry_release_id": package["source_adapter_registry_release_id"],
        "source_adapter_registry_update_id": package["source_adapter_registry_update_id"],
        "registry_rollout_status": package["registry_rollout_status"],
        "adapter_count": package["adapter_count"],
        "output_file_count": len(stored_files),
        "store_status": "STORED",
        "stored_files": stored_files,
        "verification": verification,
    }


def store_source_adapter_registry_rollout_from_files(
    registry_release_package_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    package = load_json(registry_release_package_path)
    return store_source_adapter_registry_rollout(package, output_dir)


if __name__ == "__main__":
    from tempfile import TemporaryDirectory
    from source_adapter_registry_rollout_test import _registry_release_package

    with TemporaryDirectory() as tmp:
        summary = store_source_adapter_registry_rollout(_registry_release_package(), tmp)
        assert summary["output_file_count"] == 5, summary
        assert summary["verification"]["verified"] is True, summary
    print("Source Adapter Registry Rollout store self-test passed.")
