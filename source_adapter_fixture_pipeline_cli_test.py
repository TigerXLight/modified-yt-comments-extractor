from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_adapter_fixture_pipeline_cli import main


def test_cli_writes_fixture_pipeline_package() -> None:
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
                    "source_artifact_sha256": "d" * 64,
                }
            ]
        },
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "fixture_review.json"
        output_dir = Path(tmpdir) / "out"
        input_path.write_text(json.dumps(fixture_review), encoding="utf-8")
        code = main(["--fixture-review-json", str(input_path), "--output-dir", str(output_dir), "--json"])
        assert code == 0
        assert any(path.name.endswith("source_adapter_fixture_pipeline_package.json") for path in output_dir.iterdir())


if __name__ == "__main__":
    test_cli_writes_fixture_pipeline_package()
    print("Source Adapter Fixture Pipeline CLI self-test passed.")
