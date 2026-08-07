from __future__ import annotations

from capture_manual_live_smoke_observation_packet import (
    build_capture_manual_live_smoke_observation_packet,
    capture_manual_live_smoke_observation_packet_to_json,
)

_GOOD_HASH = "a" * 64


def test_manual_live_smoke_observation_packet_is_metadata_only_and_safe() -> None:
    packet = build_capture_manual_live_smoke_observation_packet(
        [
            {
                "site_id": "msn-news",
                "display_name": "MSN News",
                "requested_action": "manual comments overlay observation",
                "operator_summary": "Operator observed the comments region and saved a local metadata note.",
                "observed_artifacts": [
                    {
                        "file_name": "msn-comments-note.json",
                        "sha256": _GOOD_HASH,
                        "byte_count": 123,
                        "role": "operator_note_metadata",
                    }
                ],
            }
        ],
        packet_id="msn-observation-packet",
    )
    data = packet.to_dict()
    assert data["schema_version"] == "capture_manual_live_smoke_observation_packet_v1"
    assert data["observation_count"] == 1
    assert data["manual_operator_observation_supplied"] is True
    assert data["live_network_request_performed_by_tool"] is False
    assert data["browser_automation_performed_by_tool"] is False
    assert data["credential_value_read_by_tool"] is False
    assert data["raw_media_payload_included"] is False
    assert data["full_local_path_serialized"] is False
    assert data["completed_capture_claimed"] is False
    assert data["verified_capture_claimed"] is False
    rendered = capture_manual_live_smoke_observation_packet_to_json(packet)
    assert "msn-comments-note.json" in rendered
    assert "C:\\" not in rendered
    assert "/mnt/" not in rendered


def test_manual_live_smoke_observation_packet_rejects_secret_fields_and_paths() -> None:
    try:
        build_capture_manual_live_smoke_observation_packet(
            [
                {
                    "site_id": "msn-news",
                    "requested_action": "manual observation",
                    "operator_summary": "safe",
                    "api_key": "not allowed",
                }
            ]
        )
    except ValueError as exc:
        assert "secret-like field" in str(exc)
    else:
        raise AssertionError("secret-like fields must be rejected")

    try:
        build_capture_manual_live_smoke_observation_packet(
            [
                {
                    "site_id": "msn-news",
                    "requested_action": "manual observation",
                    "operator_summary": "safe",
                    "observed_artifacts": [
                        {
                            "file_name": "C:\\Users\\fahad\\note.json",
                            "sha256": _GOOD_HASH,
                            "byte_count": 1,
                        }
                    ],
                }
            ]
        )
    except ValueError as exc:
        assert "full local path" in str(exc) or "path separators" in str(exc)
    else:
        raise AssertionError("full local paths must be rejected")


if __name__ == "__main__":
    test_manual_live_smoke_observation_packet_is_metadata_only_and_safe()
    test_manual_live_smoke_observation_packet_rejects_secret_fields_and_paths()
    print("Manual live smoke observation packet self-test passed.")
