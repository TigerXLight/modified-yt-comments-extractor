from __future__ import annotations

import json

from capture_msn_manual_approved_release_package import (
    MSN_MANUAL_APPROVED_RELEASE_PACKAGE_STATUS_NEEDS_REVIEW,
    MSN_MANUAL_APPROVED_RELEASE_PACKAGE_STATUS_READY,
    build_msn_manual_approved_release_package,
    msn_manual_approved_release_package_to_json,
)


def _handoff() -> dict[str, object]:
    return {
        "schema_version": "msn_manual_approved_export_handoff_v1",
        "handoff_id": "msn.queue.approved_export.1234",
        "queue_item_id": "msn.queue",
        "decision_id": "msn.queue.approved.1234",
        "source_url": "https://www.msn.com/en-gb/news/example",
        "named_site": "msn",
        "named_action": "msn_manual_capture",
        "article_title": "Example MSN Article",
        "review_decision": "APPROVED",
        "handoff_status": "APPROVED_EXPORT_HANDOFF_READY",
        "ready_for_total_export_release": True,
        "issue_count": 0,
        "assets": [
            {"role": "article_text", "filename": "article.txt", "sha256": "a" * 64, "byte_count": 100},
            {"role": "comments_json", "filename": "comments.json", "sha256": "b" * 64, "byte_count": 200},
        ],
        "evidence_queue_update": {"queue_item_id": "msn.queue", "queue_status": "READY_FOR_TOTAL_EXPORT_RELEASE"},
        "total_export_handoff": {"queue_item_id": "msn.queue", "handoff_status": "READY_FOR_TOTAL_EXPORT_RELEASE"},
        "safety_flags": {
            "metadata_only_handoff": True,
            "explicit_decision_json_only": True,
            "no_live_http": True,
            "no_browser_automation": True,
            "no_full_local_paths": True,
            "no_credential_reads": True,
        },
    }


def _package_store() -> dict[str, object]:
    return {
        "schema_version": "msn_manual_total_export_package_store_v1",
        "store_status": "STORED",
        "stored_files": [
            {"role": "total_export_manifest", "filename": "manifest.json", "sha256": "c" * 64, "byte_count": 300}
        ],
    }


def test_build_ready_release_package() -> None:
    report = build_msn_manual_approved_release_package(_handoff(), package_store_report=_package_store(), release_label="release 1")
    assert report.release_status == MSN_MANUAL_APPROVED_RELEASE_PACKAGE_STATUS_READY
    assert report.ready_for_total_export_release is True
    assert report.issue_count == 0
    assert report.evidence_queue_update["queue_status"] == "TOTAL_EXPORT_RELEASE_READY"
    assert report.total_export_release_manifest["asset_count"] == 3
    assert report.safety_flags["no_browser_automation"] is True
    assert report.release_hash
    payload = json.loads(msn_manual_approved_release_package_to_json(report))
    assert payload["schema_version"] == "msn_manual_approved_release_package_v1"
    assert payload["release_label"] == "release_1"


def test_rejects_full_paths() -> None:
    handoff = _handoff()
    handoff["article_title"] = r"T:\References\private-title.txt"
    try:
        build_msn_manual_approved_release_package(handoff)
    except ValueError as exc:
        assert "full local paths" in str(exc)
    else:
        raise AssertionError("expected full local path rejection")


def test_non_ready_handoff_needs_review() -> None:
    handoff = _handoff()
    handoff["handoff_status"] = "APPROVED_EXPORT_HANDOFF_NEEDS_REVIEW"
    report = build_msn_manual_approved_release_package(handoff)
    assert report.release_status == MSN_MANUAL_APPROVED_RELEASE_PACKAGE_STATUS_NEEDS_REVIEW
    assert report.ready_for_total_export_release is False
    assert report.issue_count >= 1


if __name__ == "__main__":
    test_build_ready_release_package()
    test_rejects_full_paths()
    test_non_ready_handoff_needs_review()
    print("MSN manual approved release package self-test passed.")
