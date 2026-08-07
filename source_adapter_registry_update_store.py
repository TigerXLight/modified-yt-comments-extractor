from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

from source_adapter_registry_update import build_source_adapter_registry_update, load_json, write_json_file

STORE_SCHEMA_VERSION = "source_adapter_registry_update_store_v1"


def _json_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stored_file(path: Path, role: str) -> dict[str, Any]:
    return {
        "role": role,
        "filename": path.name,
        "byte_count": path.stat().st_size,
        "sha256": _json_hash(path),
    }


def store_source_adapter_registry_update(
    adapter_registry_handoff: Mapping[str, Any],
    output_dir: str | Path,
    existing_registry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    package = build_source_adapter_registry_update(adapter_registry_handoff, existing_registry=existing_registry)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    update_id = package["source_adapter_registry_update_id"]
    outputs = [
        ("source_adapter_registry_update_package", package),
        ("source_adapter_registry_update_record", package["adapter_registry_record"]),
        ("source_adapter_readiness_index", package["adapter_readiness_index"]),
        ("source_adapter_registry_release_handoff", package["adapter_registry_release_handoff"]),
        ("source_adapter_registry_update_operator_summary", package["operator_summary"]),
    ]
    stored_files: list[dict[str, Any]] = []
    for role, data in outputs:
        path = destination / f"{update_id}.{role}.json"
        write_json_file(path, data)
        stored_files.append(_stored_file(path, role))
    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "source_adapter_registry_update_id": update_id,
        "source_adapter_coverage_acceptance_id": package["source_adapter_coverage_acceptance_id"],
        "registry_update_status": package["registry_update_status"],
        "adapter_count": package["adapter_count"],
        "output_file_count": len(stored_files),
        "store_status": "STORED",
        "stored_files": stored_files,
    }


def store_source_adapter_registry_update_from_files(
    adapter_registry_handoff_path: str | Path,
    output_dir: str | Path,
    existing_registry_path: str | Path | None = None,
) -> dict[str, Any]:
    handoff = load_json(adapter_registry_handoff_path)
    existing = load_json(existing_registry_path) if existing_registry_path else None
    return store_source_adapter_registry_update(handoff, output_dir, existing_registry=existing)


if __name__ == "__main__":
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as tmp:
        summary = store_source_adapter_registry_update(
            {
                "source_adapter_coverage_acceptance_id": "source_adapter_coverage_acceptance.example",
                "handoff_status": "READY_FOR_ADAPTER_REGISTRY_UPDATE",
                "adapters": [
                    {
                        "adapter_id": "article",
                        "coverage_status": "ACCEPTED_SHARED_FIXTURE_COVERAGE",
                        "shared_stage_coverage": ["content_extraction"],
                        "accepted_for_shared_pipeline": True,
                    }
                ],
            },
            tmp,
        )
        assert summary["output_file_count"] == 5, summary
    print("Source Adapter Registry Update store self-test passed.")
