from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from source_adapter_coverage_acceptance import build_source_adapter_coverage_acceptance, write_json_file
from source_adapter_coverage_acceptance_verifier import verify_source_adapter_coverage_acceptance

STORE_SCHEMA_VERSION = "source_adapter_coverage_acceptance_store_v1"


def _json_bytes(data: Mapping[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"


def _file_record(path: Path, *, role: str) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "role": role,
        "filename": path.name,
        "byte_count": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def store_source_adapter_coverage_acceptance(
    fixture_pipeline_closeout: Mapping[str, Any],
    output_dir: str | Path,
    traceability_index: Mapping[str, Any] | None = None,
    acceptance_handoff: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    package = build_source_adapter_coverage_acceptance(fixture_pipeline_closeout, traceability_index, acceptance_handoff)
    verification = verify_source_adapter_coverage_acceptance(package)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    acceptance_id = package["source_adapter_coverage_acceptance_id"]
    outputs = [
        ("source_adapter_coverage_acceptance_package", package),
        ("source_adapter_coverage_acceptance_record", package["acceptance_record"]),
        ("source_adapter_registry_handoff", package["adapter_registry_handoff"]),
        ("source_adapter_coverage_acceptance_operator_summary", package["operator_summary"]),
    ]
    stored_files: list[dict[str, Any]] = []
    for role, data in outputs:
        path = output_path / f"{acceptance_id}.{role}.json"
        write_json_file(path, data)
        stored_files.append(_file_record(path, role=role))
    record = {
        "schema_version": STORE_SCHEMA_VERSION,
        "store_status": "STORED",
        "source_adapter_coverage_acceptance_id": acceptance_id,
        "source_adapter_fixture_pipeline_closeout_id": package["source_adapter_fixture_pipeline_closeout_id"],
        "source_adapter_fixture_pipeline_id": package["source_adapter_fixture_pipeline_id"],
        "acceptance_status": package["acceptance_status"],
        "adapter_count": package["adapter_count"],
        "accepted_adapter_count": package["accepted_adapter_count"],
        "fixture_count": package["fixture_count"],
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
        "verification": verification,
    }
    (output_path / f"{acceptance_id}.source_adapter_coverage_acceptance_store.json").write_bytes(_json_bytes(record))
    return record
