from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from source_adapter_fixture_matrix import SCHEMA_VERSION, SHARED_PIPELINE_STAGES

VERIFIER_SCHEMA_VERSION = "source_adapter_fixture_matrix_verifier_v1"


def verify_source_adapter_fixture_matrix(matrix: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if matrix.get("schema_version") != SCHEMA_VERSION:
        issues.append("unexpected schema_version")
    adapters = matrix.get("adapters")
    if not isinstance(adapters, list) or not adapters:
        issues.append("adapters must be a non-empty array")
        adapters = []
    adapter_ids: list[str] = []
    for adapter in adapters:
        if not isinstance(adapter, Mapping):
            issues.append("each adapter must be an object")
            continue
        adapter_id = str(adapter.get("adapter_id") or "").strip()
        if not adapter_id:
            issues.append("adapter_id is required")
        if adapter_id in adapter_ids:
            issues.append(f"duplicate adapter_id: {adapter_id}")
        adapter_ids.append(adapter_id)
        if adapter.get("live_network_default") is not False:
            issues.append(f"adapter {adapter_id} must keep live_network_default false")
        for forbidden in ("path", "absolute_path", "local_path", "filesystem_path"):
            if forbidden in adapter:
                issues.append(f"adapter {adapter_id} includes forbidden local path field {forbidden}")
    fixture_matrix = matrix.get("fixture_matrix")
    if not isinstance(fixture_matrix, Mapping):
        issues.append("fixture_matrix must be an object")
        rows = []
    else:
        rows = fixture_matrix.get("rows")
        if not isinstance(rows, list) or len(rows) != len(adapters):
            issues.append("fixture_matrix.rows must match adapters length")
            rows = []
    for row in rows:
        if not isinstance(row, Mapping):
            issues.append("each fixture row must be an object")
            continue
        adapter_id = str(row.get("adapter_id") or "").strip()
        fixture_types = row.get("fixture_types")
        if not isinstance(fixture_types, list) or not fixture_types:
            issues.append(f"adapter {adapter_id} must declare fixture_types")
        if row.get("required_fixture_files_started") is not False:
            issues.append(f"adapter {adapter_id} must not mark fixture files as started")
    binding = matrix.get("shared_pipeline_binding")
    if not isinstance(binding, Mapping):
        issues.append("shared_pipeline_binding must be an object")
    else:
        stages = binding.get("stages")
        if not isinstance(stages, list) or len(stages) != len(SHARED_PIPELINE_STAGES):
            issues.append("shared_pipeline_binding.stages must include the full shared pipeline")
    summary = matrix.get("operator_summary")
    if not isinstance(summary, Mapping):
        issues.append("operator_summary must be an object")
    else:
        if summary.get("manual_or_live_actions_started") is not False:
            issues.append("operator_summary must not mark manual/live actions as started")
        if summary.get("live_network_default") is not False:
            issues.append("operator_summary must keep live_network_default false")
    return {
        "schema_version": VERIFIER_SCHEMA_VERSION,
        "adapter_fixture_matrix_id": matrix.get("adapter_fixture_matrix_id", ""),
        "adapter_count": matrix.get("adapter_count", 0),
        "issue_count": len(issues),
        "issues": issues,
        "verified": not issues,
    }


def verify_source_adapter_fixture_matrix_file(path: str | Path) -> dict[str, Any]:
    return verify_source_adapter_fixture_matrix(json.loads(Path(path).read_text(encoding="utf-8")))


__all__ = ["VERIFIER_SCHEMA_VERSION", "verify_source_adapter_fixture_matrix", "verify_source_adapter_fixture_matrix_file"]
