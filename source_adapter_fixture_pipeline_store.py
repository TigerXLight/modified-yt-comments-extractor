from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

from source_adapter_fixture_pipeline import build_source_adapter_fixture_pipeline, write_json_file
from source_adapter_fixture_pipeline_verifier import verify_source_adapter_fixture_pipeline

STORE_SCHEMA_VERSION = "source_adapter_fixture_pipeline_store_v1"


def _json_bytes(data: Mapping[str, Any]) -> bytes:
    import json

    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_prefix(value: object) -> str:
    text = str(value or "source_adapter_fixture_pipeline").strip().replace("/", ".").replace("\\", ".")
    return text.strip(".") or "source_adapter_fixture_pipeline"


def _write_role(output_dir: Path, prefix: str, role: str, data: Mapping[str, Any]) -> dict[str, Any]:
    payload = _json_bytes(data)
    filename = f"{prefix}.{role}.json"
    path = output_dir / filename
    path.write_bytes(payload)
    return {"role": role, "filename": filename, "byte_count": len(payload), "sha256": _sha256_bytes(payload)}


def store_source_adapter_fixture_pipeline(
    fixture_review: Mapping[str, Any],
    output_dir: str | Path,
    pipeline_results: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    package = build_source_adapter_fixture_pipeline(fixture_review, pipeline_results)
    verification = verify_source_adapter_fixture_pipeline(package)
    prefix = _safe_prefix(package["source_adapter_fixture_pipeline_id"])
    stored_files = [
        _write_role(output_path, prefix, "source_adapter_fixture_pipeline_package", package),
        _write_role(output_path, prefix, "source_adapter_fixture_execution_plan", package["fixture_execution_plan"]),
        _write_role(output_path, prefix, "source_adapter_fixture_assertion_manifest", package["fixture_assertion_manifest"]),
        _write_role(output_path, prefix, "source_adapter_fixture_pipeline_closeout_handoff", package["fixture_pipeline_closeout_handoff"]),
        _write_role(output_path, prefix, "source_adapter_fixture_pipeline_operator_summary", package["operator_summary"]),
    ]
    record = {
        "schema_version": STORE_SCHEMA_VERSION,
        "source_adapter_fixture_pipeline_id": package["source_adapter_fixture_pipeline_id"],
        "source_adapter_fixture_review_id": package["source_adapter_fixture_review_id"],
        "fixture_pipeline_status": package["fixture_pipeline_status"],
        "fixture_count": package["fixture_count"],
        "planned_stage_count": package["planned_stage_count"],
        "output_file_count": len(stored_files),
        "store_status": "STORED",
        "stored_files": stored_files,
        "verification": verification,
    }
    write_json_file(output_path / f"{prefix}.source_adapter_fixture_pipeline_store.json", record)
    return record


if __name__ == "__main__":
    import tempfile

    fixture_review = {
        "source_adapter_fixture_review_id": "source_adapter_fixture_review.example",
        "review_status": "PASSED",
        "adapter_reviews": [{"adapter_id": "article", "shared_pipeline_stages": ["artifact_collection"]}],
        "fixture_registry": {
            "fixtures": [
                {
                    "adapter_id": "article",
                    "fixture_type": "saved_article_html_or_text",
                    "template_safe_basename": "article.01.saved_article_html_or_text.template.json",
                    "operator_supplied_file_required": True,
                    "fixture_review_status": "PASSED",
                    "source_artifact_safe_basename": "article.fixture.html",
                    "source_artifact_sha256": "a" * 64,
                }
            ]
        },
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        result = store_source_adapter_fixture_pipeline(fixture_review, tmpdir)
        assert result["store_status"] == "STORED", result
        assert result["output_file_count"] == 5, result
    print("Source Adapter Fixture Pipeline store self-test passed.")
