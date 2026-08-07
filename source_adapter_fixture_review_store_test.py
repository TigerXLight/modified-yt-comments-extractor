from __future__ import annotations

import tempfile
from pathlib import Path

from source_adapter_fixture_review_store import store_source_adapter_fixture_review


def _inputs() -> tuple[dict, dict]:
    authoring = {
        "source_adapter_fixture_authoring_id": "source_adapter_fixture_authoring.fixture",
        "template_index": {
            "template_rows": [
                {
                    "adapter_id": "article",
                    "artifact_role": "article_html_or_text",
                    "fixture_type": "saved_article_html_or_text",
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
                "source_artifact_sha256": "e" * 64,
                "expected_assertions": {},
            }
        ]
    }
    return authoring, authored


def test_store_writes_deterministic_outputs() -> None:
    authoring, authored = _inputs()
    with tempfile.TemporaryDirectory() as tmp:
        result = store_source_adapter_fixture_review(authoring, authored, tmp)
        assert result["schema_version"] == "source_adapter_fixture_review_store_v1"
        assert result["store_status"] == "STORED"
        assert result["output_file_count"] == 5
        assert result["review_status"] == "PASSED"
        filenames = {item["filename"] for item in result["stored_files"]}
        assert len(filenames) == 5
        for item in result["stored_files"]:
            path = Path(tmp) / item["filename"]
            assert path.exists()
            assert item["byte_count"] == len(path.read_bytes())
            assert len(item["sha256"]) == 64


if __name__ == "__main__":
    test_store_writes_deterministic_outputs()
    print("Source Adapter Fixture Review store self-test passed.")
