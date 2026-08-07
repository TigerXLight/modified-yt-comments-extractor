from __future__ import annotations

import json
import tempfile
from pathlib import Path

from capture_manual_live_smoke_approval_packet import build_capture_manual_live_smoke_approval_packet
from capture_manual_live_smoke_approval_packet_store import (
    CAPTURE_MANUAL_LIVE_SMOKE_APPROVAL_PACKET_FILENAME,
    capture_manual_live_smoke_approval_packet_store_result_to_json,
    write_capture_manual_live_smoke_approval_packet,
)


def _packet():
    return build_capture_manual_live_smoke_approval_packet(
        [
            {
                "site_id": "archive-ph",
                "display_name": "archive.ph manual check",
                "requested_action": "manual_archive_lookup",
            }
        ],
        packet_id="manual-approval-test",
    )


def test_store_writes_safe_metadata_without_full_paths() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        result = write_capture_manual_live_smoke_approval_packet(_packet(), temp_dir)
        data = result.to_dict()
        assert data["schema_version"] == "capture_manual_live_smoke_approval_packet_store_v1"
        assert data["file_count"] == 1
        assert data["files"][0]["filename"] == CAPTURE_MANUAL_LIVE_SMOKE_APPROVAL_PACKET_FILENAME
        written = Path(temp_dir) / CAPTURE_MANUAL_LIVE_SMOKE_APPROVAL_PACKET_FILENAME
        assert written.exists()
        assert data["files"][0]["byte_count"] == len(written.read_bytes())
        assert data["files"][0]["sha256"]
        assert data["live_network_request_performed"] is False
        assert data["browser_automation_performed"] is False
        assert data["completed_capture_claimed"] is False
        payload = capture_manual_live_smoke_approval_packet_store_result_to_json(result)
        assert temp_dir not in payload
        assert "manual-approval-test" in payload
        stored = json.loads(written.read_text(encoding="utf-8"))
        assert stored["packet_id"] == "manual-approval-test"


def test_store_refuses_overwrite_when_requested() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        write_capture_manual_live_smoke_approval_packet(_packet(), temp_dir)
        try:
            write_capture_manual_live_smoke_approval_packet(
                _packet(),
                temp_dir,
                allow_overwrite=False,
            )
        except FileExistsError as exc:
            assert CAPTURE_MANUAL_LIVE_SMOKE_APPROVAL_PACKET_FILENAME in str(exc)
        else:
            raise AssertionError("expected overwrite refusal")


if __name__ == "__main__":
    test_store_writes_safe_metadata_without_full_paths()
    test_store_refuses_overwrite_when_requested()
    print("Manual live smoke approval packet store self-test passed.")
