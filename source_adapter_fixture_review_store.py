from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

from source_adapter_fixture_review import build_source_adapter_fixture_review, write_json_file

STORE_SCHEMA_VERSION = "source_adapter_fixture_review_store_v1"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _byte_count(path: Path) -> int:
    return len(path.read_bytes())


def store_source_adapter_fixture_review(
    fixture_authoring: Mapping[str, Any],
    authored_fixtures: Mapping[str, Any],
    output_dir: str | Path,
) -> dict[str, Any]:
    package = build_source_adapter_fixture_review(fixture_authoring, authored_fixtures)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    review_id = str(package["source_adapter_fixture_review_id"])
    files = [
        ("source_adapter_fixture_review_package", package),
        ("source_adapter_authored_fixture_registry", package["fixture_registry"]),
        ("source_adapter_fixture_pipeline_handoff", package["fixture_pipeline_handoff"]),
        ("source_adapter_fixture_review_report", package["fixture_review_report"]),
        ("source_adapter_fixture_review_operator_summary", package["operator_summary"]),
    ]
    stored_files: list[dict[str, Any]] = []
    for role, data in files:
        filename = f"{review_id}.{role}.json"
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
        "source_adapter_fixture_review_id": review_id,
        "source_adapter_fixture_authoring_id": package.get("source_adapter_fixture_authoring_id", ""),
        "source_adapter_fixture_matrix_id": package.get("source_adapter_fixture_matrix_id", ""),
        "adapter_count": package["adapter_count"],
        "fixture_count": package["fixture_count"],
        "review_status": package["review_status"],
        "output_file_count": len(stored_files),
        "stored_files": stored_files,
    }


if __name__ == "__main__":
    import tempfile

    authoring = {
        "source_adapter_fixture_authoring_id": "source_adapter_fixture_authoring.example",
        "template_index": {
            "template_rows": [
                {
                    "adapter_id": "article",
                    "fixture_type": "saved_article_html_or_text",
                    "artifact_role": "article_html_or_text",
                    "operator_supplied_file_required": True,
                    "safe_template_basename": "article.01.saved_article_html_or_text.template.json",
                }
            ]
        },
        "shared_stage_route_plan": {"adapters": [{"adapter_id": "article", "shared_pipeline_stages": ["artifact_collection"]}]},
    }
    authored = {
        "fixtures": [
            {
                "adapter_id": "article",
                "fixture_type": "saved_article_html_or_text",
                "template_safe_basename": "article.01.saved_article_html_or_text.template.json",
                "source_artifact_safe_basename": "article.fixture.html",
                "source_artifact_sha256": "b" * 64,
                "expected_assertions": {},
            }
        ]
    }
    with tempfile.TemporaryDirectory() as tmp:
        result = store_source_adapter_fixture_review(authoring, authored, tmp)
        assert result["output_file_count"] == 5
        assert result["review_status"] == "PASSED"
    print("Source Adapter Fixture Review store self-test passed.")
