from __future__ import annotations

import tempfile
from pathlib import Path

from source_adapter_fixture_pipeline_store import store_source_adapter_fixture_pipeline


def test_store_fixture_pipeline_outputs() -> None:
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
                    "source_artifact_sha256": "b" * 64,
                }
            ]
        },
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        record = store_source_adapter_fixture_pipeline(fixture_review, tmpdir)
        assert record["store_status"] == "STORED"
        assert record["output_file_count"] == 5
        assert record["verification"]["verified"] is True
        for stored in record["stored_files"]:
            path = Path(tmpdir) / stored["filename"]
            assert path.exists(), stored
            assert path.stat().st_size == stored["byte_count"]


if __name__ == "__main__":
    test_store_fixture_pipeline_outputs()
    print("Source Adapter Fixture Pipeline store self-test passed.")
