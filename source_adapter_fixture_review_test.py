from __future__ import annotations

from source_adapter_fixture_review import SourceAdapterFixtureReviewError, build_source_adapter_fixture_review


def _fixture_authoring() -> dict:
    return {
        "source_adapter_fixture_authoring_id": "source_adapter_fixture_authoring.fixture",
        "source_adapter_fixture_matrix_id": "source_adapter_fixture_matrix.fixture",
        "template_index": {
            "template_rows": [
                {
                    "adapter_id": "article",
                    "artifact_role": "article_html_or_text",
                    "fixture_type": "saved_article_html_or_text",
                    "operator_supplied_file_required": True,
                    "safe_template_basename": "article.01.saved_article_html_or_text.template.json",
                },
                {
                    "adapter_id": "article",
                    "artifact_role": "expected_content_extraction_json",
                    "fixture_type": "expected_content_extraction_json",
                    "operator_supplied_file_required": False,
                    "safe_template_basename": "article.02.expected_content_extraction_json.template.json",
                },
            ]
        },
        "shared_stage_route_plan": {
            "adapters": [
                {
                    "adapter_id": "article",
                    "shared_pipeline_stages": [
                        "artifact_collection",
                        "content_extraction",
                        "total_export_package",
                        "pipeline_closeout",
                    ],
                }
            ]
        },
    }


def _authored_fixtures() -> dict:
    return {
        "schema_version": "source_adapter_authored_fixtures_v1",
        "source_adapter_fixture_authoring_id": "source_adapter_fixture_authoring.fixture",
        "fixtures": [
            {
                "adapter_id": "article",
                "fixture_type": "saved_article_html_or_text",
                "template_safe_basename": "article.01.saved_article_html_or_text.template.json",
                "source_artifact_safe_basename": "article.fixture.html",
                "source_artifact_sha256": "d" * 64,
                "expected_assertions": {},
            },
            {
                "adapter_id": "article",
                "fixture_type": "expected_content_extraction_json",
                "template_safe_basename": "article.02.expected_content_extraction_json.template.json",
                "source_artifact_safe_basename": "",
                "source_artifact_sha256": "",
                "expected_assertions": {"title_contains": "Fixture title", "minimum_body_chars": 25},
            },
        ],
    }


def test_builds_passed_fixture_review_package() -> None:
    result = build_source_adapter_fixture_review(_fixture_authoring(), _authored_fixtures())
    assert result["schema_version"] == "source_adapter_fixture_review_package_v1"
    assert result["source_adapter_fixture_review_id"].startswith("source_adapter_fixture_review.")
    assert result["review_status"] == "PASSED"
    assert result["issue_count"] == 0
    assert result["adapter_count"] == 1
    assert result["fixture_count"] == 2
    assert result["fixture_pipeline_handoff"]["handoff_status"] == "READY_FOR_SHARED_PIPELINE_FIXTURE_RUN"
    assert result["fixture_pipeline_handoff"]["manual_or_live_actions_started"] is False
    assert result["operator_summary"]["live_network_default"] is False


def test_blocks_missing_required_operator_artifact() -> None:
    authored = _authored_fixtures()
    authored["fixtures"][0]["source_artifact_safe_basename"] = ""
    authored["fixtures"][0]["source_artifact_sha256"] = ""
    result = build_source_adapter_fixture_review(_fixture_authoring(), authored)
    assert result["review_status"] == "BLOCKED"
    assert result["issue_count"] >= 2
    assert result["fixture_pipeline_handoff"]["handoff_status"] == "BLOCKED_BY_FIXTURE_REVIEW"


def test_rejects_local_path_fields() -> None:
    authored = _authored_fixtures()
    authored["fixtures"][0]["local_path"] = "C:/secret/source.html"
    try:
        build_source_adapter_fixture_review(_fixture_authoring(), authored)
    except SourceAdapterFixtureReviewError as exc:
        assert "local path fields" in str(exc)
    else:
        raise AssertionError("local path field was not rejected")


if __name__ == "__main__":
    test_builds_passed_fixture_review_package()
    test_blocks_missing_required_operator_artifact()
    test_rejects_local_path_fields()
    print("Source Adapter Fixture Review self-test passed.")
