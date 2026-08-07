from __future__ import annotations

from source_adapter_fixture_review import build_source_adapter_fixture_review
from source_adapter_fixture_review_verifier import verify_source_adapter_fixture_review


def _package() -> dict:
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
                "source_artifact_sha256": "a" * 64,
                "expected_assertions": {},
            }
        ]
    }
    return build_source_adapter_fixture_review(authoring, authored)


def test_verifier_accepts_package() -> None:
    result = verify_source_adapter_fixture_review(_package())
    assert result["verified"] is True
    assert result["issue_count"] == 0


def test_verifier_rejects_live_started_flag() -> None:
    package = _package()
    package["operator_summary"]["manual_or_live_actions_started"] = True
    result = verify_source_adapter_fixture_review(package)
    assert result["verified"] is False
    assert any("manual/live" in issue for issue in result["issues"])


if __name__ == "__main__":
    test_verifier_accepts_package()
    test_verifier_rejects_live_started_flag()
    print("Source Adapter Fixture Review verifier self-test passed.")
