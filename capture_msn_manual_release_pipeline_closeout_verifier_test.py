from capture_msn_manual_release_pipeline_closeout import build_msn_manual_release_pipeline_closeout
from capture_msn_manual_release_pipeline_closeout_verifier import verify_msn_manual_release_pipeline_closeout


def test_verifier_accepts_complete_packet():
    packet = build_msn_manual_release_pipeline_closeout(
        {
            "queue_item_id": "msn.queue",
            "release_id": "msn.queue.release.1234",
            "stored_files": [{"filename": "safe.json", "role": "safe", "sha256": "c" * 64, "byte_count": 33}],
        }
    )
    result = verify_msn_manual_release_pipeline_closeout(packet)
    assert result["verified"] is True
    assert result["issue_count"] == 0


def test_verifier_rejects_absolute_path():
    packet = build_msn_manual_release_pipeline_closeout(
        {
            "queue_item_id": "msn.queue",
            "release_id": "msn.queue.release.1234",
            "stored_files": [{"filename": "safe.json", "role": "safe", "sha256": "d" * 64, "byte_count": 44}],
        }
    )
    packet["operator_next_actions"].append(r"Copy from T:\References\unsafe")
    result = verify_msn_manual_release_pipeline_closeout(packet)
    assert result["verified"] is False
    assert any("absolute_path" in issue for issue in result["issues"])


if __name__ == "__main__":
    test_verifier_accepts_complete_packet()
    test_verifier_rejects_absolute_path()
    print("MSN manual release pipeline closeout verifier self-test passed.")
