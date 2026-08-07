from __future__ import annotations

from source_adapter_fixture_pipeline_closeout import (
    SourceAdapterFixturePipelineCloseoutError,
    build_source_adapter_fixture_pipeline_closeout,
)


def _passed_pipeline() -> dict:
    return {
        "source_adapter_fixture_pipeline_id": "source_adapter_fixture_pipeline.example",
        "source_adapter_fixture_review_id": "source_adapter_fixture_review.example",
        "source_adapter_fixture_authoring_id": "source_adapter_fixture_authoring.example",
        "source_adapter_fixture_matrix_id": "source_adapter_fixture_matrix.example",
        "fixture_pipeline_status": "PASSED",
        "fixture_count": 1,
        "planned_stage_count": 1,
        "result_count": 1,
        "issue_count": 0,
        "issues": [],
        "fixture_execution_plan": {
            "stage_rows": [
                {
                    "adapter_id": "article",
                    "stage_id": "content_extraction",
                    "execution_mode": "local_fixture_only",
                    "fixture_count": 1,
                    "fixture_types": ["expected_content_extraction_json"],
                    "template_safe_basenames": ["article.expected.json"],
                }
            ]
        },
        "fixture_assertion_manifest": {
            "assertion_rows": [
                {
                    "adapter_id": "article",
                    "fixture_type": "expected_content_extraction_json",
                    "template_safe_basename": "article.expected.json",
                    "expected_assertion_keys": ["title"],
                }
            ]
        },
        "stage_results": [
            {
                "adapter_id": "article",
                "stage_id": "content_extraction",
                "result_status": "PASS",
                "assertions_checked": ["title"],
                "issue_count": 0,
                "issues": [],
            }
        ],
    }


def test_closes_passed_fixture_pipeline() -> None:
    package = build_source_adapter_fixture_pipeline_closeout(_passed_pipeline())
    assert package["closeout_status"] == "FIXTURE_PIPELINE_CLOSED"
    assert package["adapter_acceptance_handoff"]["handoff_status"] == "READY_FOR_ADAPTER_COVERAGE_ACCEPTANCE"
    assert package["closeout_record"]["manual_or_live_actions_started"] is False
    assert package["traceability_index"]["planned_stage_count"] == 1


def test_ready_pipeline_waits_for_explicit_results() -> None:
    pipeline = _passed_pipeline()
    pipeline["fixture_pipeline_status"] = "READY_FOR_LOCAL_FIXTURE_EXECUTION"
    pipeline["stage_results"] = []
    pipeline["result_count"] = 0
    package = build_source_adapter_fixture_pipeline_closeout(pipeline)
    assert package["closeout_status"] == "READY_FOR_LOCAL_FIXTURE_RESULTS"
    assert package["adapter_acceptance_handoff"]["handoff_status"] == "WAITING_FOR_LOCAL_FIXTURE_RESULTS"


def test_failed_pipeline_is_blocked() -> None:
    pipeline = _passed_pipeline()
    pipeline["fixture_pipeline_status"] = "FAILED"
    pipeline["issue_count"] = 1
    pipeline["issues"] = ["stage result blocked or failed: article:content_extraction"]
    package = build_source_adapter_fixture_pipeline_closeout(pipeline)
    assert package["closeout_status"] == "FIXTURE_PIPELINE_BLOCKED"
    assert package["adapter_acceptance_handoff"]["handoff_status"] == "BLOCKED_BY_FIXTURE_PIPELINE"


def test_rejects_local_path_fields() -> None:
    pipeline = _passed_pipeline()
    pipeline["fixture_execution_plan"]["local_path"] = "C:/secret/result.json"
    try:
        build_source_adapter_fixture_pipeline_closeout(pipeline)
    except SourceAdapterFixturePipelineCloseoutError as exc:
        assert "local_path" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected local path rejection")


if __name__ == "__main__":
    test_closes_passed_fixture_pipeline()
    test_ready_pipeline_waits_for_explicit_results()
    test_failed_pipeline_is_blocked()
    test_rejects_local_path_fields()
    print("Source Adapter Fixture Pipeline Closeout self-test passed.")
