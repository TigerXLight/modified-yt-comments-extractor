from __future__ import annotations

from source_approved_release import build_source_approved_release


def _assert_raises(expected_error: type[BaseException], expected_text: str, func, *args, **kwargs) -> None:
    try:
        func(*args, **kwargs)
    except expected_error as exc:
        assert expected_text in str(exc)
        return
    raise AssertionError(f"expected {expected_error.__name__} containing {expected_text!r}")


def _review_package():
    return {
        "schema_version": "source_evidence_review_v1",
        "evidence_review_package_id": "fixture_adapter.evidence_review.1234",
        "queue_item_id": "fixture_adapter.evidence_queue.1234",
        "total_export_package_id": "fixture_adapter.total_export_package.1234",
        "capture_bundle_id": "fixture_adapter.capture_bundle.1234",
        "adapter_id": "fixture_adapter",
        "source_url": "https://fixture.test/story",
        "review_package_status": "READY_FOR_REVIEW_DECISION",
        "content_summary": {"title": "Fixture Story", "body_character_count": 123},
        "comment_summary": {"comment_count": 2, "reply_count": 1},
        "artifact_count": 2,
        "artifact_index": [
            {"role": "article_html_or_text", "filename": "article.html", "sha256": "a" * 64, "byte_count": 42, "source_stage": "source_evidence_review"},
            {"role": "comments_json_or_text", "filename": "comments.json", "sha256": "b" * 64, "byte_count": 52, "source_stage": "source_evidence_review"},
        ],
        "required_review_actions": ["verify_source_identity", "review_content_text", "decide_evidence_status"],
    }


def _review_decision():
    return {
        "schema_version": "source_evidence_review_decision_v1",
        "evidence_review_package_id": "fixture_adapter.evidence_review.1234",
        "queue_item_id": "fixture_adapter.evidence_queue.1234",
        "decision": "APPROVED",
        "review_status": "APPROVED_FOR_RELEASE",
        "reviewer_id": "reviewer",
        "approved_for_release": True,
        "revision_required": False,
        "completed_action_ids": ["verify_source_identity", "review_content_text", "decide_evidence_status"],
        "missing_required_action_ids": [],
        "review_notes": ["Approved after artifact review."],
    }


def _release_handoff():
    return {
        "schema_version": "source_evidence_review_release_handoff_v1",
        "evidence_review_package_id": "fixture_adapter.evidence_review.1234",
        "queue_item_id": "fixture_adapter.evidence_queue.1234",
        "total_export_package_id": "fixture_adapter.total_export_package.1234",
        "capture_bundle_id": "fixture_adapter.capture_bundle.1234",
        "adapter_id": "fixture_adapter",
        "source_url": "https://fixture.test/story",
        "handoff_status": "READY_FOR_APPROVED_RELEASE",
        "required_next_stage": "source_approved_release",
        "decision": "APPROVED",
        "release_inputs": [
            {"role": "source_evidence_review_package", "id": "fixture_adapter.evidence_review.1234", "filename_hint": "review.json"},
            {"role": "source_evidence_review_decision", "id": "fixture_adapter.evidence_review.1234", "filename_hint": "decision.json"},
        ],
    }



def test_build_source_approved_release_outputs_release_ready_package() -> None:
    outputs = build_source_approved_release(
        evidence_review_package=_review_package(),
        evidence_review_decision=_review_decision(),
        release_handoff=_release_handoff(),
        releaser_id="release_operator",
        release_notes=["Ready for index."],
    )
    package = outputs.approved_release_package
    assert package["schema_version"] == "source_approved_release_v1"
    assert package["release_status"] == "READY_FOR_RELEASE_INDEX"
    assert package["approved_by_review_decision"] is True
    assert package["artifact_count"] == 2
    assert package["release_fingerprint"]
    assert outputs.release_index_handoff["required_next_stage"] == "source_release_index"
    assert outputs.operator_summary["manual_or_live_actions_started"] is False


def test_build_source_approved_release_rejects_non_approved_decision() -> None:
    decision = _review_decision()
    decision["decision"] = "REVISION_REQUESTED"
    decision["approved_for_release"] = False
    _assert_raises(
        ValueError,
        "only APPROVED",
        build_source_approved_release,
        evidence_review_package=_review_package(),
        evidence_review_decision=decision,
    )


def test_build_source_approved_release_rejects_artifact_paths() -> None:
    package = _review_package()
    package["artifact_index"][0]["filename"] = r"C:\tmp\article.html"
    _assert_raises(
        ValueError,
        "safe basenames",
        build_source_approved_release,
        evidence_review_package=package,
        evidence_review_decision=_review_decision(),
    )


if __name__ == "__main__":
    test_build_source_approved_release_outputs_release_ready_package()
    test_build_source_approved_release_rejects_non_approved_decision()
    test_build_source_approved_release_rejects_artifact_paths()
    print("Source Approved Release self-test passed.")
