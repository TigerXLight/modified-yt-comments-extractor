from __future__ import annotations

from source_adapter_fixture_pipeline import build_source_adapter_fixture_pipeline
from source_adapter_fixture_pipeline_verifier import verify_source_adapter_fixture_pipeline


def _package() -> dict:
    return build_source_adapter_fixture_pipeline(
        {
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
                        "source_artifact_sha256": "c" * 64,
                    }
                ]
            },
        }
    )


def test_verifier_accepts_valid_package() -> None:
    result = verify_source_adapter_fixture_pipeline(_package())
    assert result["verified"] is True
    assert result["issue_count"] == 0


def test_verifier_rejects_mutated_counts() -> None:
    package = _package()
    package["planned_stage_count"] = 99
    result = verify_source_adapter_fixture_pipeline(package)
    assert result["verified"] is False
    assert any("planned_stage_count" in issue for issue in result["issues"])


if __name__ == "__main__":
    test_verifier_accepts_valid_package()
    test_verifier_rejects_mutated_counts()
    print("Source Adapter Fixture Pipeline verifier self-test passed.")
