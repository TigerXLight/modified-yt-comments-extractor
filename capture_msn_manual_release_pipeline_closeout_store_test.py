import tempfile
from pathlib import Path

from capture_msn_manual_release_pipeline_closeout import build_msn_manual_release_pipeline_closeout
from capture_msn_manual_release_pipeline_closeout_store import store_msn_manual_release_pipeline_closeout


def test_store_pipeline_closeout():
    packet = build_msn_manual_release_pipeline_closeout(
        {
            "queue_item_id": "msn.queue",
            "release_id": "msn.queue.release.1234",
            "stored_files": [{"filename": "safe.json", "role": "safe", "sha256": "b" * 64, "byte_count": 22}],
        }
    )
    with tempfile.TemporaryDirectory() as tmp:
        result = store_msn_manual_release_pipeline_closeout(packet, tmp)
        assert result["schema_version"] == "msn_manual_release_pipeline_closeout_store_v1"
        assert result["output_file_count"] == 3
        for item in result["stored_files"]:
            assert Path(tmp, item["filename"]).exists()
            assert len(item["sha256"]) == 64
            assert item["byte_count"] > 0


if __name__ == "__main__":
    test_store_pipeline_closeout()
    print("MSN manual release pipeline closeout store self-test passed.")
