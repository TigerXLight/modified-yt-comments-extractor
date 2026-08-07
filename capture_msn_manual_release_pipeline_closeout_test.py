from capture_msn_manual_release_pipeline_closeout import (
    PIPELINE_STATUS_CLOSED,
    build_msn_manual_release_pipeline_closeout,
    inspect_msn_manual_release_pipeline_closeout_safety,
)


def _closeout():
    return {
        "queue_item_id": "msn.queue",
        "release_id": "msn.queue.release.1234",
        "closeout_id": "msn.queue.release.1234.closeout.abc123",
        "export_bundle_id": "msn.queue.release.1234.export_bundle.def456",
        "stored_files": [
            {
                "filename": "msn.queue.release.1234.closeout.abc123.release_section_closeout.json",
                "role": "msn_manual_release_section_closeout",
                "sha256": "a" * 64,
                "byte_count": 111,
            }
        ],
    }


def test_build_pipeline_closeout():
    packet = build_msn_manual_release_pipeline_closeout(_closeout(), operator_label="reviewer")
    assert packet["schema_version"] == "msn_manual_release_pipeline_closeout_v1"
    assert packet["pipeline_status"] == PIPELINE_STATUS_CLOSED
    assert packet["queue_item_id"] == "msn.queue"
    assert packet["release_id"] == "msn.queue.release.1234"
    assert packet["operator_label"] == "reviewer"
    assert packet["stage_coverage"]["release_section_closeout"] is True
    assert packet["stored_file_count"] == 1
    assert packet["transition_map"]["to_status"] == "TOTAL_EXPORT_RELEASE_READY_FOR_OPERATOR_ARCHIVAL"
    assert packet["pipeline_closeout_id"].startswith("msn.queue.release.1234.pipeline_closeout.")
    assert inspect_msn_manual_release_pipeline_closeout_safety(packet)["safe"] is True


def test_missing_stage_requires_review():
    source = _closeout()
    source["stage_coverage"] = {"release_section_closeout": True}
    packet = build_msn_manual_release_pipeline_closeout(source)
    assert packet["pipeline_status"] == "MSN_MANUAL_RELEASE_PIPELINE_REVIEW_REQUIRED"
    assert "manual_action_kit" in packet["missing_stages"]


if __name__ == "__main__":
    test_build_pipeline_closeout()
    test_missing_stage_requires_review()
    print("MSN manual release pipeline closeout self-test passed.")
