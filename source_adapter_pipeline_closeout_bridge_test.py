from __future__ import annotations

from copy import deepcopy

from source_adapter_pipeline_closeout_bridge import build_source_adapter_pipeline_closeout_bridge
from source_adapter_pipeline_closeout_bridge_verifier import verify_source_adapter_pipeline_closeout_bridge


def fixture_archive_review_bridge() -> dict:
    archive_review_package = {
        "schema_version": "source_archive_review_v1",
        "archive_review_package_id": "fixture_adapter.archive_review.1234",
        "archive_result_intake_id": "fixture_adapter.archive_result_intake.1234",
        "archive_handoff_id": "fixture_adapter.archive_handoff.1234",
        "release_audit_id": "fixture_adapter.release_audit.1234",
        "release_index_id": "fixture_adapter.release_index.1234",
        "approved_release_id": "fixture_adapter.approved_release.1234",
        "total_export_package_id": "fixture_adapter.total_export_package.1234",
        "queue_item_id": "fixture_adapter.evidence_queue.1234",
        "adapter_id": "fixture_adapter",
        "source_url": "https://fixture.test/story",
        "decision": "APPROVED",
        "reviewed_receipts": [
            {"provider_id": "archive_today", "archive_url": "https://archive.today/example", "review_status": "ACCEPTED"},
            {"provider_id": "ghostarchive", "archive_url": "https://ghostarchive.org/archive/example", "review_status": "ACCEPTED"},
        ],
        "source_artifacts": [
            {"role": "article_html_or_text", "filename": "article.html", "byte_count": 21, "sha256": "a" * 64},
            {"role": "comments_json_or_text", "filename": "comments.json", "byte_count": 31, "sha256": "b" * 64},
        ],
    }
    archive_review_decision = {
        "archive_review_decision_id": "fixture_adapter.archive_review_decision.1234",
        "archive_review_package_id": "fixture_adapter.archive_review.1234",
        "adapter_id": "fixture_adapter",
        "source_url": "https://fixture.test/story",
        "decision": "APPROVED",
    }
    archive_review_closeout = {
        "archive_review_closeout_id": "fixture_adapter.archive_review_closeout.1234",
        "archive_review_package_id": "fixture_adapter.archive_review.1234",
        "adapter_id": "fixture_adapter",
        "source_url": "https://fixture.test/story",
        "decision": "APPROVED",
        "closeout_status": "ARCHIVE_COMPLETE",
    }
    return {
        "schema_version": "source_adapter_archive_review_bridge_v1",
        "archive_review_bridge_status": "SHARED_ARCHIVE_REVIEWS_BUILT",
        "source_adapter_archive_review_bridge_id": "source_adapter_archive_review_bridge.example",
        "archive_review_count": 1,
        "issue_count": 0,
        "issues": [],
        "archive_review_outputs": [
            {
                "archive_review_package": archive_review_package,
                "archive_review_checklist": {"schema_version": "source_archive_review_checklist_v1"},
                "archive_review_decision": archive_review_decision,
                "archive_review_closeout": archive_review_closeout,
                "operator_summary": {"schema_version": "source_archive_review_operator_summary_v1"},
            }
        ],
        "source_adapter_pipeline_closeout_batch_handoff": {
            "schema_version": "source_adapter_pipeline_closeout_batch_handoff_v1",
            "handoff_status": "READY_FOR_SHARED_PIPELINE_CLOSEOUT",
            "ready_for_pipeline_closeout": True,
            "required_next_stage": "source_pipeline_closeout",
            "archive_review_package_ids": ["fixture_adapter.archive_review.1234"],
            "archive_result_intake_ids": ["fixture_adapter.archive_result_intake.1234"],
            "pipeline_closeout_inputs": [
                {
                    "role": "source_archive_review_closeout",
                    "id": "fixture_adapter.archive_review.1234",
                    "filename_hint": "fixture_adapter.archive_review.1234.source_archive_review_closeout.json",
                }
            ],
        },
    }


def test_build_source_adapter_pipeline_closeout_bridge() -> None:
    package = build_source_adapter_pipeline_closeout_bridge(fixture_archive_review_bridge(), operator_notes=["close shared fixture flow"])
    assert package["pipeline_closeout_bridge_status"] == "SHARED_PIPELINE_CLOSEOUTS_BUILT"
    assert package["pipeline_closeout_count"] == 1
    assert package["source_adapter_pipeline_closeout_batch"]["complete_count"] == 1
    assert package["source_adapter_shared_pipeline_roadmap_closeout_handoff"]["handoff_status"] == "SOURCE_ADAPTER_SHARED_PIPELINE_COMPLETE"
    assert package["pipeline_closeout_outputs"][0]["closeout_report"]["final_status"] == "SOURCE_PIPELINE_COMPLETE"
    assert verify_source_adapter_pipeline_closeout_bridge(package)["verified"] is True


def test_rejects_unready_pipeline_handoff() -> None:
    fixture = fixture_archive_review_bridge()
    fixture["source_adapter_pipeline_closeout_batch_handoff"]["ready_for_pipeline_closeout"] = False
    try:
        build_source_adapter_pipeline_closeout_bridge(fixture)
    except ValueError as exc:
        assert "ready_for_pipeline_closeout" in str(exc)
    else:
        raise AssertionError("expected unready pipeline handoff rejection")


def test_follow_up_archive_review_blocks_verified_closeout() -> None:
    fixture = fixture_archive_review_bridge()
    fixture = deepcopy(fixture)
    output = fixture["archive_review_outputs"][0]
    output["archive_review_decision"]["decision"] = "REVISION_REQUESTED"
    output["archive_review_closeout"]["decision"] = "REVISION_REQUESTED"
    output["archive_review_closeout"]["closeout_status"] = "REVISION_REQUESTED"
    package = build_source_adapter_pipeline_closeout_bridge(fixture)
    assert package["pipeline_closeout_bridge_status"] == "SHARED_PIPELINE_CLOSEOUTS_BUILT"
    assert package["source_adapter_pipeline_closeout_batch"]["follow_up_count"] == 1
    assert package["source_adapter_shared_pipeline_roadmap_closeout_handoff"]["shared_pipeline_complete"] is False
    assert verify_source_adapter_pipeline_closeout_bridge(package)["verified"] is False


if __name__ == "__main__":
    test_build_source_adapter_pipeline_closeout_bridge()
    test_rejects_unready_pipeline_handoff()
    test_follow_up_archive_review_blocks_verified_closeout()
    print("Source Adapter Pipeline Closeout Bridge self-test passed.")
