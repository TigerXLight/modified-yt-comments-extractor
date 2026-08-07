from __future__ import annotations

from source_release_audit import build_source_release_audit


def _release_index_record():
    return {
        "schema_version": "source_release_index_v1",
        "release_index_id": "fixture_adapter.release_index.1234",
        "release_index_status": "READY_FOR_RELEASE_EXPORT_BUNDLE",
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
            {"role": "article_html_or_text", "filename": "article.html", "sha256": "a" * 64, "byte_count": 42, "source_stage": "source_release_index"},
            {"role": "comments_json_or_text", "filename": "comments.json", "sha256": "b" * 64, "byte_count": 52, "source_stage": "source_release_index"},
        ],
        "release_fingerprint": "f" * 16,
        "index_fingerprint": "i" * 16,
        "release_notes": ["Indexed for export bundle."],
    }


def _release_inventory():
    return {
        "schema_version": "source_release_inventory_v1",
        "release_index_id": "fixture_adapter.release_index.1234",
        "inventory_status": "READY_FOR_RELEASE_EXPORT_BUNDLE",
        "adapter_id": "fixture_adapter",
        "source_url": "https://fixture.test/story",
        "release_count": 1,
        "release_entries": [
            {
                "approved_release_id": "fixture_adapter.approved_release.1234",
                "artifact_count": 2,
                "artifact_roles": ["article_html_or_text", "comments_json_or_text"],
            }
        ],
    }


def _export_bundle_handoff():
    return {
        "schema_version": "source_release_export_bundle_handoff_v1",
        "release_index_id": "fixture_adapter.release_index.1234",
        "approved_release_id": "fixture_adapter.approved_release.1234",
        "queue_item_id": "fixture_adapter.evidence_queue.1234",
        "total_export_package_id": "fixture_adapter.total_export_package.1234",
        "capture_bundle_id": "fixture_adapter.capture_bundle.1234",
        "adapter_id": "fixture_adapter",
        "source_url": "https://fixture.test/story",
        "handoff_status": "READY_FOR_RELEASE_EXPORT_BUNDLE",
        "required_next_stage": "source_release_export_bundle",
        "release_export_inputs": [],
    }


def test_source_release_audit_builds_archive_handoff() -> None:
    outputs = build_source_release_audit(
        release_index_record=_release_index_record(),
        release_inventory=_release_inventory(),
        export_bundle_handoff=_export_bundle_handoff(),
        auditor_id="release_auditor",
        audit_notes=["Ready for archive handoff."],
    )
    report = outputs.release_audit_report
    assert report["schema_version"] == "source_release_audit_v1"
    assert report["audit_status"] == "READY_FOR_ARCHIVE_HANDOFF"
    assert report["release_index_id"] == "fixture_adapter.release_index.1234"
    assert report["audited_by"] == "release_auditor"
    assert all(check["status"] == "PASS" for check in report["audit_checks"])
    assert outputs.traceability_map["traceability_status"] == "READY_FOR_ARCHIVE_HANDOFF"
    assert outputs.archive_handoff["required_next_stage"] == "source_archive_handoff"
    assert outputs.archive_handoff["archive_submission_started"] is False
    assert outputs.operator_summary["manual_or_live_actions_started"] is False


def test_source_release_audit_rejects_wrong_status() -> None:
    record = _release_index_record()
    record["release_index_status"] = "PENDING"
    try:
        build_source_release_audit(release_index_record=record)
    except ValueError as exc:
        assert "READY_FOR_RELEASE_EXPORT_BUNDLE" in str(exc)
    else:
        raise AssertionError("expected invalid release index status to fail")


def test_source_release_audit_rejects_path_artifacts() -> None:
    record = _release_index_record()
    record["artifact_index"][0]["filename"] = r"C:\\tmp\\article.html"
    try:
        build_source_release_audit(release_index_record=record)
    except ValueError as exc:
        assert "safe basenames" in str(exc)
    else:
        raise AssertionError("expected path artifact to fail")


if __name__ == "__main__":
    test_source_release_audit_builds_archive_handoff()
    test_source_release_audit_rejects_wrong_status()
    test_source_release_audit_rejects_path_artifacts()
    print("Source Release Audit self-test passed.")
