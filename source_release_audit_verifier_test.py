from __future__ import annotations

from source_release_audit import build_source_release_audit
from source_release_audit_verifier import verify_source_release_audit


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
        "artifact_index": [
            {"role": "article_html_or_text", "filename": "article.html", "sha256": "a" * 64, "byte_count": 42, "source_stage": "source_release_index"},
        ],
        "release_fingerprint": "f" * 16,
        "index_fingerprint": "i" * 16,
    }


def test_source_release_audit_verifier_accepts_valid_bundle() -> None:
    outputs = build_source_release_audit(release_index_record=_release_index_record())
    result = verify_source_release_audit(outputs.release_audit_report, outputs.traceability_map, outputs.archive_handoff)
    assert result["verified"] is True
    assert result["issue_count"] == 0


def test_source_release_audit_verifier_rejects_started_archive() -> None:
    outputs = build_source_release_audit(release_index_record=_release_index_record())
    handoff = dict(outputs.archive_handoff)
    handoff["archive_submission_started"] = True
    result = verify_source_release_audit(outputs.release_audit_report, outputs.traceability_map, handoff)
    assert result["verified"] is False
    assert any("archive submission" in issue for issue in result["issues"])


if __name__ == "__main__":
    test_source_release_audit_verifier_accepts_valid_bundle()
    test_source_release_audit_verifier_rejects_started_archive()
    print("Source Release Audit verifier self-test passed.")
