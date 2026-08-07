from __future__ import annotations

import json
from tempfile import TemporaryDirectory

from capture_manual_live_smoke_observation_packet import build_capture_manual_live_smoke_observation_packet
from capture_manual_live_smoke_observation_packet_store import (
    CAPTURE_MANUAL_LIVE_SMOKE_OBSERVATION_PACKET_FILENAME,
    capture_manual_live_smoke_observation_packet_store_result_to_json,
    write_capture_manual_live_smoke_observation_packet,
)

_GOOD_HASH = "b" * 64


def _packet():
    return build_capture_manual_live_smoke_observation_packet(
        [
            {
                "site_id": "telegraph-news",
                "display_name": "Telegraph News",
                "requested_action": "manual article observation",
                "operator_summary": "Operator supplied safe metadata only.",
                "observed_artifacts": [
                    {
                        "file_name": "telegraph-note.json",
                        "sha256": _GOOD_HASH,
                        "byte_count": 44,
                        "role": "operator_note_metadata",
                    }
                ],
            }
        ]
    )


def test_observation_packet_store_writes_safe_result_without_full_paths() -> None:
    with TemporaryDirectory() as directory:
        result = write_capture_manual_live_smoke_observation_packet(_packet(), directory)
        data = result.to_dict()
        written = __import__("pathlib").Path(directory) / CAPTURE_MANUAL_LIVE_SMOKE_OBSERVATION_PACKET_FILENAME
        assert written.exists()
        assert data["files"][0]["file_name"] == CAPTURE_MANUAL_LIVE_SMOKE_OBSERVATION_PACKET_FILENAME
        assert data["files"][0]["byte_count"] == len(written.read_bytes())
        assert data["full_local_path_serialized"] is False
        assert data["completed_capture_claimed"] is False
        rendered = capture_manual_live_smoke_observation_packet_store_result_to_json(result)
        assert directory not in rendered
        assert "telegraph-note.json" not in rendered
        parsed = json.loads(rendered)
        assert parsed["schema_version"] == "capture_manual_live_smoke_observation_packet_store_v1"


def test_observation_packet_store_refuses_overwrite_when_requested() -> None:
    with TemporaryDirectory() as directory:
        write_capture_manual_live_smoke_observation_packet(_packet(), directory)
        try:
            write_capture_manual_live_smoke_observation_packet(
                _packet(), directory, allow_overwrite=False
            )
        except FileExistsError as exc:
            assert CAPTURE_MANUAL_LIVE_SMOKE_OBSERVATION_PACKET_FILENAME in str(exc)
        else:
            raise AssertionError("overwrite refusal did not trigger")


if __name__ == "__main__":
    test_observation_packet_store_writes_safe_result_without_full_paths()
    test_observation_packet_store_refuses_overwrite_when_requested()
    print("Manual live smoke observation packet store self-test passed.")
