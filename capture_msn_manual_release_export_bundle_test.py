from __future__ import annotations

from capture_msn_manual_release_export_bundle import (
    MSN_MANUAL_RELEASE_EXPORT_BUNDLE_STATUS_READY,
    build_msn_manual_release_export_bundle,
    msn_manual_release_export_bundle_to_json,
)


def _release_index() -> dict[str, object]:
    return {
        "schema_version": "msn_manual_release_index_v1",
        "index_id": "msn.queue.release.1234.index.e9bb1eeef9ad",
        "release_id": "msn.queue.release.1234",
        "queue_item_id": "msn.queue",
        "source_url": "https://www.msn.com/en-gb/news/example/ar-AA1234",
        "named_site": "msn",
        "named_action": "msn_manual_capture",
        "article_title": "Example article",
        "release_index_status": "MSN_MANUAL_RELEASE_INDEX_READY",
        "ready_for_total_export_release_index": True,
        "issue_count": 0,
        "assets": [
            {"role": "msn_manual_release_index", "filename": "release_index.json", "sha256": "a" * 64, "byte_count": 10},
            {"role": "msn_manual_release_inventory", "filename": "release_inventory.json", "sha256": "b" * 64, "byte_count": 20},
            {"role": "msn_manual_release_queue_update", "filename": "release_queue_update.json", "sha256": "c" * 64, "byte_count": 30},
        ],
        "evidence_queue_release_update": {"queue_status": "TOTAL_EXPORT_RELEASE_INDEXED"},
        "total_export_release_handoff": {"handoff_status": "TOTAL_EXPORT_RELEASE_INDEX_READY"},
        "safety_flags": {
            "metadata_only_release_index": True,
            "explicit_release_package_json_only": True,
            "no_live_http": True,
            "no_browser_automation": True,
            "no_full_local_paths": True,
            "no_credential_reads": True,
        },
    }


def test_build_ready_release_export_bundle() -> None:
    report = build_msn_manual_release_export_bundle(_release_index())
    payload = msn_manual_release_export_bundle_to_json(report)
    assert report.export_bundle_status == MSN_MANUAL_RELEASE_EXPORT_BUNDLE_STATUS_READY
    assert report.ready_for_total_export_handoff is True
    assert report.issue_count == 0
    assert payload["total_export_handoff_manifest"]["handoff_status"] == "TOTAL_EXPORT_HANDOFF_READY"
    assert payload["evidence_queue_final_update"]["queue_status"] == "TOTAL_EXPORT_HANDOFF_READY"
    assert payload["checksum_manifest"]["checksum_status"] == "CHECKSUMS_READY"
    assert payload["safety_flags"]["no_file_moves"] is True


def test_rejects_full_local_paths() -> None:
    payload = _release_index()
    payload["source_url"] = r"C:\\Users\\fahad\\capture.html"
    try:
        build_msn_manual_release_export_bundle(payload)
    except ValueError as exc:
        assert "full local paths" in str(exc)
    else:
        raise AssertionError("expected full path rejection")


if __name__ == "__main__":
    test_build_ready_release_export_bundle()
    test_rejects_full_local_paths()
    print("MSN manual release export bundle self-test passed.")
