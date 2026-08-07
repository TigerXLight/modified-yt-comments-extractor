from __future__ import annotations

from capture_msn_manual_release_section_closeout import (
    MSN_MANUAL_RELEASE_SECTION_CLOSEOUT_STATUS_READY,
    build_msn_manual_release_section_closeout,
    msn_manual_release_section_closeout_to_json,
)


def _bundle() -> dict[str, object]:
    return {
        "schema_version": "msn_manual_release_export_bundle_v1",
        "export_bundle_id": "msn.queue.release.1234.export_bundle.aaaabbbbcccc",
        "index_id": "msn.queue.release.1234.index.e9bb1eeef9ad",
        "release_id": "msn.queue.release.1234",
        "queue_item_id": "msn.queue",
        "source_url": "https://www.msn.com/en-gb/news/example",
        "named_site": "msn",
        "named_action": "msn_manual_capture",
        "article_title": "Example MSN article",
        "export_bundle_status": "MSN_MANUAL_RELEASE_EXPORT_BUNDLE_READY",
        "ready_for_total_export_handoff": True,
        "issue_count": 0,
        "assets": [{"role": "article_text", "filename": "article.txt", "sha256": "a" * 64, "byte_count": 10}],
        "total_export_handoff_manifest": {"handoff_status": "TOTAL_EXPORT_HANDOFF_READY"},
        "evidence_queue_final_update": {"queue_status": "TOTAL_EXPORT_HANDOFF_READY"},
        "checksum_manifest": {"checksum_status": "CHECKSUMS_READY", "sha256_by_filename": {"article.txt": "a" * 64}},
        "safety_flags": {
            "metadata_only_export_bundle": True,
            "explicit_release_index_json_only": True,
            "no_live_http": True,
            "no_browser_automation": True,
            "no_archive_submission": True,
            "no_media_downloads": True,
            "no_credential_reads": True,
            "no_folder_scans": True,
            "no_file_moves": True,
            "no_full_local_paths": True,
        },
    }


def _store() -> dict[str, object]:
    return {
        "schema_version": "msn_manual_release_export_bundle_store_v1",
        "store_status": "STORED",
        "export_bundle_id": "msn.queue.release.1234.export_bundle.aaaabbbbcccc",
        "release_id": "msn.queue.release.1234",
        "queue_item_id": "msn.queue",
        "output_file_count": 3,
        "stored_files": [
            {"role": "msn_manual_release_export_bundle", "filename": "bundle.json", "sha256": "b" * 64, "byte_count": 100},
            {"role": "msn_manual_release_export_manifest", "filename": "manifest.json", "sha256": "c" * 64, "byte_count": 80},
            {"role": "msn_manual_release_export_queue_update", "filename": "queue.json", "sha256": "d" * 64, "byte_count": 40},
        ],
    }


def test_build_closeout_ready() -> None:
    report = build_msn_manual_release_section_closeout(_bundle(), release_export_bundle_store_report=_store())
    payload = msn_manual_release_section_closeout_to_json(report)
    assert report.closeout_status == MSN_MANUAL_RELEASE_SECTION_CLOSEOUT_STATUS_READY
    assert report.ready_for_total_export_release_record is True
    assert report.issue_count == 0
    assert payload["total_export_release_record"]["release_record_status"] == "TOTAL_EXPORT_RELEASE_RECORD_READY"
    assert payload["evidence_queue_closeout_update"]["queue_status"] == "TOTAL_EXPORT_RELEASE_CLOSED"
    assert payload["final_release_checklist"]["checksums_ready"] is True


def test_build_closeout_rejects_full_paths() -> None:
    bundle = _bundle()
    bundle["operator_path"] = "C:\\Users\\fahad\\Desktop\\artifact.html"
    try:
        build_msn_manual_release_section_closeout(bundle)
    except ValueError as exc:
        assert "full local paths" in str(exc)
    else:
        raise AssertionError("full local path was not rejected")


if __name__ == "__main__":
    test_build_closeout_ready()
    test_build_closeout_rejects_full_paths()
    print("MSN manual release section closeout self-test passed.")
