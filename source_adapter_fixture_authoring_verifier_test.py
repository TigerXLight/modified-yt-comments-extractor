from __future__ import annotations

from source_adapter_fixture_authoring import build_source_adapter_fixture_authoring
from source_adapter_fixture_authoring_verifier import verify_source_adapter_fixture_authoring


def test_verifier_accepts_valid_package() -> None:
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
    result = verify_source_adapter_fixture_authoring(build_source_adapter_fixture_authoring(matrix))
    assert result["verified"] is True
    assert result["issue_count"] == 0


def test_verifier_rejects_started_live_actions() -> None:
    package = build_source_adapter_fixture_authoring(
        {
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
    )
    package["operator_summary"]["manual_or_live_actions_started"] = True
    result = verify_source_adapter_fixture_authoring(package)
    assert result["verified"] is False
    assert result["issue_count"] == 1


if __name__ == "__main__":
    test_verifier_accepts_valid_package()
    test_verifier_rejects_started_live_actions()
    print("Source Adapter Fixture Authoring verifier self-test passed.")
