from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, Sequence

from source_adapter_fixture_authoring import build_source_adapter_fixture_authoring, write_json_file

STORE_SCHEMA_VERSION = "source_adapter_fixture_authoring_store_v1"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _byte_count(path: Path) -> int:
    return len(path.read_bytes())


def store_source_adapter_fixture_authoring(
    fixture_matrix: Mapping[str, Any],
    output_dir: str | Path,
    *,
    adapter_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    package = build_source_adapter_fixture_authoring(fixture_matrix, adapter_ids=adapter_ids)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    authoring_id = str(package["source_adapter_fixture_authoring_id"])
    files = [
        ("source_adapter_fixture_authoring_package", package),
        ("source_adapter_fixture_template_index", package["template_index"]),
        ("source_adapter_fixture_route_plan", package["shared_stage_route_plan"]),
        ("source_adapter_fixture_review_handoff", package["fixture_review_handoff"]),
        ("source_adapter_fixture_authoring_operator_summary", package["operator_summary"]),
    ]
    stored_files: list[dict[str, Any]] = []
    for role, data in files:
        filename = f"{authoring_id}.{role}.json"
        path = output / filename
        write_json_file(path, data)
        stored_files.append(
            {
                "role": role,
                "filename": filename,
                "byte_count": _byte_count(path),
                "sha256": _sha256_file(path),
            }
        )
    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "store_status": "STORED",
        "source_adapter_fixture_authoring_id": authoring_id,
        "source_adapter_fixture_matrix_id": package.get("source_adapter_fixture_matrix_id", ""),
        "adapter_count": package["adapter_count"],
        "fixture_template_count": package["fixture_template_count"],
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
    }


if __name__ == "__main__":
    import tempfile

    matrix = {
        "fixture_matrix": {
            "rows": [
                {
                    "adapter_id": "article",
                    "fixture_types": ["saved_article_html_or_text", "expected_pipeline_closeout_json"],
                    "shared_pipeline_stages": ["artifact_collection", "pipeline_closeout"],
                }
            ]
        }
    }
    with tempfile.TemporaryDirectory() as tmp:
        result = store_source_adapter_fixture_authoring(matrix, tmp)
        assert result["output_file_count"] == 5
    print("Source Adapter Fixture Authoring store self-test passed.")
