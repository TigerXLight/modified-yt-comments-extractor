from __future__ import annotations

from source_adapter_coverage_acceptance import (
    SourceAdapterCoverageAcceptanceError,
    build_source_adapter_coverage_acceptance,
)


def _accepted_closeout() -> dict:
    return {
        "source_adapter_fixture_pipeline_closeout_id": "source_adapter_fixture_pipeline_closeout.example",
        "source_adapter_fixture_pipeline_id": "source_adapter_fixture_pipeline.example",
        "source_adapter_fixture_review_id": "source_adapter_fixture_review.example",
        "source_adapter_fixture_authoring_id": "source_adapter_fixture_authoring.example",
        "source_adapter_fixture_matrix_id": "source_adapter_fixture_matrix.example",
        "closeout_status": "FIXTURE_PIPELINE_CLOSED",
        "fixture_count": 1,
        "planned_stage_count": 1,
        "result_count": 1,
        "issue_count": 0,
        "issues": [],
        "traceability_index": {
            "adapters": ["article"],
            "fixture_count": 1,
            "planned_stage_count": 1,
            "result_count": 1,
            "stage_rows": [
                {"adapter_id": "article", "stage_id": "content_extraction", "execution_mode": "local_fixture_only", "fixture_count": 1}
            ],
            "result_rows": [
                {"adapter_id": "article", "stage_id": "content_extraction", "result_status": "PASS", "issue_count": 0}
            ],
        },
        "adapter_acceptance_handoff": {
            "source_adapter_fixture_pipeline_closeout_id": "source_adapter_fixture_pipeline_closeout.example",
            "handoff_status": "READY_FOR_ADAPTER_COVERAGE_ACCEPTANCE",
        },
    }


def test_accepts_closed_fixture_pipeline_coverage() -> None:
    package = build_source_adapter_coverage_acceptance(_accepted_closeout())
    assert package["acceptance_status"] == "ADAPTER_COVERAGE_ACCEPTED"
    assert package["accepted_adapter_count"] == 1
    assert package["adapter_registry_handoff"]["handoff_status"] == "READY_FOR_ADAPTER_REGISTRY_UPDATE"
    assert package["adapter_registry_handoff"]["adapters"][0]["accepted_for_shared_pipeline"] is True


def test_waits_for_local_fixture_results() -> None:
    closeout = _accepted_closeout()
    closeout["closeout_status"] = "READY_FOR_LOCAL_FIXTURE_RESULTS"
    closeout["adapter_acceptance_handoff"]["handoff_status"] = "WAITING_FOR_LOCAL_FIXTURE_RESULTS"
    package = build_source_adapter_coverage_acceptance(closeout)
    assert package["acceptance_status"] == "WAITING_FOR_LOCAL_FIXTURE_RESULTS"
    assert package["accepted_adapter_count"] == 0


def test_blocks_mismatched_handoff() -> None:
    closeout = _accepted_closeout()
    package = build_source_adapter_coverage_acceptance(
        closeout,
        acceptance_handoff={
            "source_adapter_fixture_pipeline_closeout_id": "different.closeout",
            "handoff_status": "READY_FOR_ADAPTER_COVERAGE_ACCEPTANCE",
        },
    )
    assert package["acceptance_status"] == "ADAPTER_COVERAGE_ACCEPTANCE_BLOCKED"
    assert any("does not match" in issue for issue in package["issues"])


def test_rejects_local_path_fields() -> None:
    closeout = _accepted_closeout()
    closeout["traceability_index"]["local_path"] = "C:/secret/fixture.json"
    try:
        build_source_adapter_coverage_acceptance(closeout)
    except SourceAdapterCoverageAcceptanceError as exc:
        assert "local_path" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected local path rejection")


if __name__ == "__main__":
    test_accepts_closed_fixture_pipeline_coverage()
    test_waits_for_local_fixture_results()
    test_blocks_mismatched_handoff()
    test_rejects_local_path_fields()
    print("Source Adapter Coverage Acceptance self-test passed.")
