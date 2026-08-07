from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

from source_adapter_fixture_matrix import build_source_adapter_fixture_matrix, write_json_file
from source_adapter_fixture_matrix_verifier import verify_source_adapter_fixture_matrix

STORE_SCHEMA_VERSION = "source_adapter_fixture_matrix_store_v1"


def store_source_adapter_fixture_matrix(
    adapter_specs: Iterable[Mapping[str, Any]],
    output_dir: str | Path,
    *,
    pipeline_closeout: Mapping[str, Any] | None = None,
    notes: Iterable[str] | None = None,
) -> dict[str, Any]:
    matrix = build_source_adapter_fixture_matrix(adapter_specs, pipeline_closeout=pipeline_closeout, notes=notes)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    matrix_id = str(matrix["adapter_fixture_matrix_id"])
    files = [
        write_json_file(destination / f"{matrix_id}.adapter_registry.json", matrix["adapter_registry"]),
        write_json_file(destination / f"{matrix_id}.fixture_matrix.json", matrix["fixture_matrix"]),
        write_json_file(destination / f"{matrix_id}.fixture_authoring_plan.json", matrix["fixture_authoring_plan"]),
        write_json_file(destination / f"{matrix_id}.shared_pipeline_binding.json", matrix["shared_pipeline_binding"]),
        write_json_file(destination / f"{matrix_id}.operator_summary.json", matrix["operator_summary"]),
    ]
    verification = verify_source_adapter_fixture_matrix(matrix)
    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "store_status": "STORED",
        "adapter_fixture_matrix_id": matrix_id,
        "adapter_count": matrix["adapter_count"],
        "output_file_count": len(files),
        "stored_files": files,
        "verification": verification,
    }


__all__ = ["STORE_SCHEMA_VERSION", "store_source_adapter_fixture_matrix"]
