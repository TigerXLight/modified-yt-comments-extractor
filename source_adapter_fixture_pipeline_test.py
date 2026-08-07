from __future__ import annotations

from source_adapter_fixture_pipeline import SourceAdapterFixturePipelineError, build_source_adapter_fixture_pipeline


def _fixture_review() -> dict:
    return {
        "source_adapter_fixture_review_id": "source_adapter_fixture_review.example",
        "source_adapter_fixture_authoring_id": "source_adapter_fixture_authoring.example",
        "source_adapter_fixture_matrix_id": "source_adapter_fixture_matrix.example",
        "review_status": "PASSED",
        "adapter_reviews": [{"adapter_id": "article", "shared_pipeline_stages": ["artifact_collection", "content_extraction"]}],
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
                    "expected_assertion_keys": [],
                },
                {
                    "adapter_id": "article",
                    "fixture_type": "expected_content_extraction_json",
                    "template_safe_basename": "article.02.expected_content_extraction_json.template.json",
                    "operator_supplied_file_required": False,
                    "fixture_review_status": "PASSED",
                    "expected_assertion_keys": ["title", "body"],
                },
            ]
        },
    }


def test_build_ready_pipeline_without_stage_results() -> None:
    package = build_source_adapter_fixture_pipeline(_fixture_review())
    assert package["fixture_pipeline_status"] == "READY_FOR_LOCAL_FIXTURE_EXECUTION"
    assert package["fixture_count"] == 2
    assert package["planned_stage_count"] == 2
    assert package["result_count"] == 0
    assert package["issue_count"] == 0
    assert package["fixture_execution_plan"]["manual_or_live_actions_started"] is False
    assert package["fixture_execution_plan"]["live_network_default"] is False
    assert package["fixture_pipeline_closeout_handoff"]["handoff_status"] == "READY_FOR_FIXTURE_PIPELINE_CLOSEOUT"


def test_build_passed_pipeline_with_explicit_local_stage_results() -> None:
    package = build_source_adapter_fixture_pipeline(
        _fixture_review(),
        {
            "stage_results": [
                {"adapter_id": "article", "stage_id": "artifact_collection", "result_status": "PASS", "assertions_checked": ["sha256"]},
                {"adapter_id": "article", "stage_id": "content_extraction", "result_status": "PASS", "assertions_checked": ["title"]},
            ]
        },
    )
    assert package["fixture_pipeline_status"] == "PASSED"
    assert package["result_count"] == 2
    assert package["issue_count"] == 0


def test_blocked_review_does_not_enter_passed_pipeline() -> None:
    review = _fixture_review()
    review["review_status"] = "BLOCKED"
    package = build_source_adapter_fixture_pipeline(review)
    assert package["fixture_pipeline_status"] == "BLOCKED_BY_FIXTURE_REVIEW"
    assert package["issue_count"] == 1


def test_rejects_local_path_fields() -> None:
    review = _fixture_review()
    review["fixture_registry"]["fixtures"][0]["local_path"] = "C:/secret/input.html"
    try:
        build_source_adapter_fixture_pipeline(review)
    except SourceAdapterFixturePipelineError as exc:
        assert "local_path" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected local path rejection")


if __name__ == "__main__":
    test_build_ready_pipeline_without_stage_results()
    test_build_passed_pipeline_with_explicit_local_stage_results()
    test_blocked_review_does_not_enter_passed_pipeline()
    test_rejects_local_path_fields()
    print("Source Adapter Fixture Pipeline self-test passed.")
