from __future__ import annotations

from source_archive_handoff import build_source_archive_handoff


def _release_audit_report():
    return {
        "schema_version": "source_release_audit_v1",
        "release_audit_id": "fixture_adapter.release_audit.1234",
        "audit_status": "READY_FOR_ARCHIVE_HANDOFF",
        "release_index_id": "fixture_adapter.release_index.1234",
        "approved_release_id": "fixture_adapter.approved_release.1234",
        "evidence_review_package_id": "fixture_adapter.evidence_review.1234",
        "queue_item_id": "fixture_adapter.evidence_queue.1234",
        "total_export_package_id": "fixture_adapter.total_export_package.1234",
        "capture_bundle_id": "fixture_adapter.capture_bundle.1234",
        "adapter_id": "fixture_adapter",
        "source_url": "https://fixture.test/story",
        "artifact_count": 2,
        "artifact_roles": ["article_html_or_text", "comments_json_or_text"],
        "artifact_index": [
            {"role": "article_html_or_text", "filename": "article.html", "sha256": "a" * 64, "byte_count": 42, "source_stage": "source_release_audit"},
            {"role": "comments_json_or_text", "filename": "comments.json", "sha256": "b" * 64, "byte_count": 52, "source_stage": "source_release_audit"},
        ],
        "audit_fingerprint": "f" * 16,
        "audit_notes": ["Audited for archive handoff."],
    }


def _traceability_map():
    return {
        "schema_version": "source_release_traceability_map_v1",
        "release_audit_id": "fixture_adapter.release_audit.1234",
        "release_index_id": "fixture_adapter.release_index.1234",
        "approved_release_id": "fixture_adapter.approved_release.1234",
        "traceability_status": "READY_FOR_ARCHIVE_HANDOFF",
        "traceability_nodes": [],
        "traceability_edges": [],
    }


def _release_archive_handoff():
    return {
        "schema_version": "source_release_archive_handoff_v1",
        "release_audit_id": "fixture_adapter.release_audit.1234",
        "release_index_id": "fixture_adapter.release_index.1234",
        "approved_release_id": "fixture_adapter.approved_release.1234",
        "handoff_status": "READY_FOR_ARCHIVE_HANDOFF",
        "required_next_stage": "source_archive_handoff",
        "archive_submission_started": False,
        "manual_or_live_actions_started": False,
    }


def test_source_archive_handoff_builds_manual_provider_tasks() -> None:
    outputs = build_source_archive_handoff(
        release_audit_report=_release_audit_report(),
        traceability_map=_traceability_map(),
        release_archive_handoff=_release_archive_handoff(),
        archive_providers=["archive_today", "ghostarchive"],
        operator_id="archive_operator",
        handoff_notes=["Operator will fill result templates."],
    )
    package = outputs.archive_handoff_package
    assert package["schema_version"] == "source_archive_handoff_v1"
    assert package["handoff_status"] == "READY_FOR_MANUAL_ARCHIVE_SUBMISSION"
    assert package["archive_submission_started"] is False
    assert package["manual_or_live_actions_started"] is False
    assert package["prepared_by"] == "archive_operator"
    assert package["archive_provider_count"] == 2
    assert outputs.provider_tasks["task_status"] == "PENDING_OPERATOR_ACTION"
    assert len(outputs.provider_tasks["archive_tasks"]) == 2
    assert all(task["approval_required_before_submission"] is True for task in outputs.provider_tasks["archive_tasks"])
    assert all(task["archive_submission_started"] is False for task in outputs.provider_tasks["archive_tasks"])
    assert outputs.result_templates["template_status"] == "WAITING_FOR_OPERATOR_RESULTS"
    assert all(template["archive_url"] == "" for template in outputs.result_templates["archive_result_templates"])
    assert outputs.result_intake_handoff["required_next_stage"] == "source_archive_result_intake"


def test_source_archive_handoff_rejects_wrong_audit_status() -> None:
    report = _release_audit_report()
    report["audit_status"] = "PENDING"
    try:
        build_source_archive_handoff(release_audit_report=report)
    except ValueError as exc:
        assert "READY_FOR_ARCHIVE_HANDOFF" in str(exc)
    else:
        raise AssertionError("expected invalid audit status to fail")


def test_source_archive_handoff_rejects_path_artifacts() -> None:
    report = _release_audit_report()
    report["artifact_index"][0]["filename"] = r"C:\\tmp\\article.html"
    try:
        build_source_archive_handoff(release_audit_report=report)
    except ValueError as exc:
        assert "safe basenames" in str(exc)
    else:
        raise AssertionError("expected path artifact to fail")


def test_source_archive_handoff_rejects_started_prior_handoff() -> None:
    prior = _release_archive_handoff()
    prior["archive_submission_started"] = True
    try:
        build_source_archive_handoff(release_audit_report=_release_audit_report(), release_archive_handoff=prior)
    except ValueError as exc:
        assert "must not already mark archive submission started" in str(exc)
    else:
        raise AssertionError("expected started prior handoff to fail")


if __name__ == "__main__":
    test_source_archive_handoff_builds_manual_provider_tasks()
    test_source_archive_handoff_rejects_wrong_audit_status()
    test_source_archive_handoff_rejects_path_artifacts()
    test_source_archive_handoff_rejects_started_prior_handoff()
    print("Source Archive Handoff self-test passed.")
