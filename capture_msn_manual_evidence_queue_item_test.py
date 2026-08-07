from __future__ import annotations

import json

from capture_msn_manual_evidence_queue_item import build_msn_manual_evidence_queue_item, msn_manual_evidence_queue_item_to_json

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
SHA_D = "d" * 64
SHA_E = "e" * 64
SHA_F = "f" * 64


def _pipeline_payload():
    return {
        "schema_version": "msn_manual_action_total_export_pipeline_v1",
        "source_url_host_hint": "www.msn.com",
        "package_id": "msn_manual_example",
        "pipeline_implemented": True,
        "generated_operator_action_kits": True,
        "explicit_operator_artifact_files_read": True,
        "total_export_package_written": True,
        "ready_for_total_export_review": True,
        "review_required": True,
        "total_export_manifest_file_name": "metadata/msn_manual_example_manifest.json",
        "total_export_manifest_sha256": SHA_A,
        "pipeline_report_sha256": SHA_B,
        "article_text_char_count": 120,
        "comment_count": 2,
        "live_network_request_performed_by_tool": False,
        "browser_automation_performed_by_tool": False,
        "archive_submission_performed_by_tool": False,
        "media_download_performed_by_tool": False,
        "credential_value_read": False,
        "raw_media_payload_included": False,
        "full_local_path_serialized": False,
        "completed_capture_claimed": False,
        "verified_capture_claimed": False,
        "total_export_store_result": {
            "files": [
                {"file_name": "page_capture/msn_manual_example_article_text.txt", "role": "article_text", "sha256": SHA_C, "byte_count": 120},
                {"file_name": "metadata/msn_manual_example_msn_manual_capture_bundle.json", "role": "capture_bundle_json", "sha256": SHA_D, "byte_count": 240},
                {"file_name": "metadata/msn_manual_example_manifest.json", "role": "total_export_manifest_json", "sha256": SHA_A, "byte_count": 360},
                {"file_name": "metadata/msn_manual_example_msn_manual_total_export_packet.json", "role": "total_export_packet_json", "sha256": SHA_E, "byte_count": 480},
                {"file_name": "metadata/msn_manual_example_comments.json", "role": "comments_json", "sha256": SHA_F, "byte_count": 60},
            ]
        },
    }


def test_builds_evidence_queue_item_from_pipeline_payload() -> None:
    item = build_msn_manual_evidence_queue_item(_pipeline_payload())
    payload = json.loads(msn_manual_evidence_queue_item_to_json(item))
    assert payload["ready_for_evidence_queue_review"] is True
    assert payload["item_kind"] == "msn_manual_capture_total_export_review"
    assert payload["asset_count"] == 5
    assert payload["comment_count"] == 2
    assert "total_export_manifest_json" in payload["asset_roles"]
    assert payload["full_local_path_serialized"] is False
    assert "C:\\" not in msn_manual_evidence_queue_item_to_json(item)


def test_rejects_completed_capture_claims() -> None:
    payload = _pipeline_payload()
    payload["completed_capture_claimed"] = True
    try:
        build_msn_manual_evidence_queue_item(payload)
    except ValueError as exc:
        assert "completed_capture_claimed" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected completed capture claim rejection")


if __name__ == "__main__":
    test_builds_evidence_queue_item_from_pipeline_payload()
    test_rejects_completed_capture_claims()
    print("MSN manual Evidence Queue item self-test passed.")
