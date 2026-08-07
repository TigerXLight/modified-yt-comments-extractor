from __future__ import annotations

from source_pipeline_closeout import SourcePipelineCloseoutError, build_source_pipeline_closeout
from source_pipeline_closeout_verifier import verify_source_pipeline_closeout


def _package() -> dict:
    return {
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


def _decision() -> dict:
    return {
        "archive_review_decision_id": "fixture_adapter.archive_review_decision.1234",
        "archive_review_package_id": "fixture_adapter.archive_review.1234",
        "adapter_id": "fixture_adapter",
        "source_url": "https://fixture.test/story",
        "decision": "APPROVED",
    }


def _closeout() -> dict:
    return {
        "archive_review_closeout_id": "fixture_adapter.archive_review_closeout.1234",
        "archive_review_package_id": "fixture_adapter.archive_review.1234",
        "adapter_id": "fixture_adapter",
        "source_url": "https://fixture.test/story",
        "decision": "APPROVED",
        "closeout_status": "ARCHIVE_COMPLETE",
    }


def test_build_source_pipeline_closeout_approved() -> None:
    bundle = build_source_pipeline_closeout(_package(), archive_review_decision=_decision(), archive_review_closeout=_closeout())
    report = bundle["closeout_report"]
    assert report["final_status"] == "SOURCE_PIPELINE_COMPLETE"
    assert report["manual_or_live_actions_started"] is False
    assert bundle["stage_inventory"]["stage_count"] == 15
    assert bundle["stage_inventory"]["complete_stage_count"] == 15
    assert bundle["roadmap_closeout_handoff"]["remaining_follow_up_stages"] == []
    assert verify_source_pipeline_closeout(bundle)["verified"] is True


def test_build_source_pipeline_closeout_follow_up() -> None:
    package = _package()
    package["decision"] = "REVISION_REQUESTED"
    bundle = build_source_pipeline_closeout(package)
    assert bundle["closeout_report"]["final_status"] == "FOLLOW_UP_REQUIRED"
    assert bundle["operator_summary"]["operator_action_required"] is True
    assert verify_source_pipeline_closeout(bundle)["verified"] is True


def test_rejects_local_path_fields() -> None:
    package = _package()
    package["path"] = "C:/secret/local/path.json"
    try:
        build_source_pipeline_closeout(package)
    except SourcePipelineCloseoutError as exc:
        assert "local path" in str(exc)
    else:
        raise AssertionError("expected local path rejection")


def test_rejects_unsafe_artifact_path() -> None:
    package = _package()
    package["source_artifacts"][0]["filename"] = "nested/article.html"
    try:
        build_source_pipeline_closeout(package)
    except SourcePipelineCloseoutError as exc:
        assert "safe basenames" in str(exc)
    else:
        raise AssertionError("expected unsafe artifact rejection")


if __name__ == "__main__":
    test_build_source_pipeline_closeout_approved()
    test_build_source_pipeline_closeout_follow_up()
    test_rejects_local_path_fields()
    test_rejects_unsafe_artifact_path()
    print("Source Pipeline Closeout self-test passed.")
