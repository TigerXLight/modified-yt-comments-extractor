from __future__ import annotations

import json

from capture_msn_manual_release_index import (
    MSN_MANUAL_RELEASE_INDEX_STATUS_NEEDS_REVIEW,
    MSN_MANUAL_RELEASE_INDEX_STATUS_READY,
    build_msn_manual_release_index,
    msn_manual_release_index_to_json,
)


def _approved_release() -> dict[str, object]:
    return {
        "schema_version": "msn_manual_approved_release_package_v1",
        "release_id": "msn.queue.release.1234",
        "queue_item_id": "msn.queue",
        "handoff_id": "msn.queue.approved_export.1234",
        "decision_id": "msn.queue.approved.1234",
        "source_url": "https://www.msn.com/en-gb/news/example",
        "named_site": "msn",
        "named_action": "msn_manual_capture",
        "article_title": "Example MSN Article",
        "release_status": "TOTAL_EXPORT_RELEASE_PACKAGE_READY",
        "ready_for_total_export_release": True,
        "issue_count": 0,
        "assets": [
            {"role": "article_text", "filename": "article.txt", "sha256": "a" * 64, "byte_count": 100},
            {"role": "comments_json", "filename": "comments.json", "sha256": "b" * 64, "byte_count": 200},
        ],
        "evidence_queue_update": {"queue_item_id": "msn.queue", "queue_status": "TOTAL_EXPORT_RELEASE_READY"},
        "total_export_release_manifest": {"release_id": "msn.queue.release.1234", "release_status": "TOTAL_EXPORT_RELEASE_PACKAGE_READY"},
        "safety_flags": {
            "metadata_only_release_package": True,
            "explicit_approved_handoff_json_only": True,
            "no_live_http": True,
            "no_browser_automation": True,
            "no_full_local_paths": True,
            "no_credential_reads": True,
        },
    }


def _store_report() -> dict[str, object]:
    return {
        "schema_version": "msn_manual_approved_release_package_store_v1",
        "release_id": "msn.queue.release.1234",
        "store_status": "STORED",
        "stored_files": [
            {"role": "approved_release_package", "filename": "release.json", "sha256": "c" * 64, "byte_count": 300},
            {"role": "approved_release_manifest", "filename": "manifest.json", "sha256": "d" * 64, "byte_count": 400},
        ],
    }


def test_build_ready_release_index() -> None:
    report = build_msn_manual_release_index(_approved_release(), release_package_store_report=_store_report(), index_label="release index 1")
    assert report.release_index_status == MSN_MANUAL_RELEASE_INDEX_STATUS_READY
    assert report.ready_for_total_export_release_index is True
    assert report.issue_count == 0
    assert report.evidence_queue_release_update["queue_status"] == "RELEASE_INDEX_READY"
    assert report.total_export_release_handoff["release_handoff_status"] == "READY_FOR_RELEASE_INDEX_CONSUMPTION"
    assert len(report.assets) == 4
    assert report.index_hash
    payload = json.loads(msn_manual_release_index_to_json(report))
    assert payload["schema_version"] == "msn_manual_release_index_v1"
    assert payload["index_label"] == "release_index_1"


def test_rejects_full_paths() -> None:
    release = _approved_release()
    release["article_title"] = r"T:\\References\\private-title.txt"
    try:
        build_msn_manual_release_index(release)
    except ValueError as exc:
        assert "full local paths" in str(exc)
    else:
        raise AssertionError("expected full local path rejection")


def test_non_ready_release_needs_review() -> None:
    release = _approved_release()
    release["release_status"] = "TOTAL_EXPORT_RELEASE_PACKAGE_NEEDS_REVIEW"
    report = build_msn_manual_release_index(release)
    assert report.release_index_status == MSN_MANUAL_RELEASE_INDEX_STATUS_NEEDS_REVIEW
    assert report.ready_for_total_export_release_index is False
    assert report.issue_count >= 1


if __name__ == "__main__":
    test_build_ready_release_index()
    test_rejects_full_paths()
    test_non_ready_release_needs_review()
    print("MSN manual release index self-test passed.")
