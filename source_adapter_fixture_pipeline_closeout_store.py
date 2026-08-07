from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

from source_adapter_fixture_pipeline_closeout import build_source_adapter_fixture_pipeline_closeout, write_json_file
from source_adapter_fixture_pipeline_closeout_verifier import verify_source_adapter_fixture_pipeline_closeout

STORE_SCHEMA_VERSION = "source_adapter_fixture_pipeline_closeout_store_v1"


def _json_bytes(data: Mapping[str, Any]) -> bytes:
    import json

    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_prefix(value: object) -> str:
    text = str(value or "source_adapter_fixture_pipeline_closeout").strip().replace("/", ".").replace("\\", ".")
    return text.strip(".") or "source_adapter_fixture_pipeline_closeout"


def _write_role(output_dir: Path, prefix: str, role: str, data: Mapping[str, Any]) -> dict[str, Any]:
    payload = _json_bytes(data)
    filename = f"{prefix}.{role}.json"
    path = output_dir / filename
    path.write_bytes(payload)
    return {"role": role, "filename": filename, "byte_count": len(payload), "sha256": _sha256_bytes(payload)}


def store_source_adapter_fixture_pipeline_closeout(
    fixture_pipeline: Mapping[str, Any],
    output_dir: str | Path,
    pipeline_store: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    package = build_source_adapter_fixture_pipeline_closeout(fixture_pipeline, pipeline_store)
    verification = verify_source_adapter_fixture_pipeline_closeout(package)
    prefix = _safe_prefix(package["source_adapter_fixture_pipeline_closeout_id"])
    stored_files = [
        _write_role(output_path, prefix, "source_adapter_fixture_pipeline_closeout_package", package),
        _write_role(output_path, prefix, "source_adapter_fixture_pipeline_closeout_record", package["closeout_record"]),
        _write_role(output_path, prefix, "source_adapter_fixture_pipeline_traceability_index", package["traceability_index"]),
        _write_role(output_path, prefix, "source_adapter_fixture_acceptance_handoff", package["adapter_acceptance_handoff"]),
        _write_role(output_path, prefix, "source_adapter_fixture_pipeline_closeout_operator_summary", package["operator_summary"]),
    ]
    record = {
        "schema_version": STORE_SCHEMA_VERSION,
        "source_adapter_fixture_pipeline_closeout_id": package["source_adapter_fixture_pipeline_closeout_id"],
        "source_adapter_fixture_pipeline_id": package["source_adapter_fixture_pipeline_id"],
        "closeout_status": package["closeout_status"],
        "fixture_pipeline_status": package["fixture_pipeline_status"],
        "fixture_count": package["fixture_count"],
        "output_file_count": len(stored_files),
        "store_status": "STORED",
        "stored_files": stored_files,
        "verification": verification,
    }
    write_json_file(output_path / f"{prefix}.source_adapter_fixture_pipeline_closeout_store.json", record)
    return record


if __name__ == "__main__":
    import tempfile

    pipeline = {
        "source_adapter_fixture_pipeline_id": "source_adapter_fixture_pipeline.example",
        "fixture_pipeline_status": "PASSED",
        "fixture_count": 1,
        "planned_stage_count": 1,
        "result_count": 1,
        "issue_count": 0,
        "issues": [],
        "fixture_execution_plan": {"stage_rows": [{"adapter_id": "article", "stage_id": "content_extraction", "execution_mode": "local_fixture_only", "fixture_count": 1, "fixture_types": ["expected_content_extraction_json"], "template_safe_basenames": ["article.expected.json"]}]},
        "fixture_assertion_manifest": {"assertion_rows": [{"adapter_id": "article", "fixture_type": "expected_content_extraction_json", "template_safe_basename": "article.expected.json"}]},
        "stage_results": [{"adapter_id": "article", "stage_id": "content_extraction", "result_status": "PASS", "issue_count": 0, "issues": []}],
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        result = store_source_adapter_fixture_pipeline_closeout(pipeline, tmpdir)
        assert result["store_status"] == "STORED", result
        assert result["output_file_count"] == 5, result
    print("Source Adapter Fixture Pipeline Closeout store self-test passed.")
