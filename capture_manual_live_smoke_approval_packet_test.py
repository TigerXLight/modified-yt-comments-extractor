from __future__ import annotations

from capture_manual_live_smoke_approval_packet import (
    build_capture_manual_live_smoke_approval_packet,
    capture_manual_live_smoke_approval_packet_to_json,
)


def test_packet_is_metadata_only_and_review_gated() -> None:
    packet = build_capture_manual_live_smoke_approval_packet(
        [
            {
                "site_id": "msn",
                "display_name": "MSN comments manual smoke",
                "requested_action": "manual_scroll_observation",
                "operator_notes": "Firefox RDM only after separate approval.",
            }
        ]
    )
    data = packet.to_dict()
    assert data["schema_version"] == "capture_manual_live_smoke_approval_packet_v1"
    assert data["review_status"] == "APPROVAL_REQUIRED"
    assert data["execution_mode"] == "MANUAL_OPERATOR_ONLY"
    assert data["target_count"] == 1
    assert data["targets"][0]["site_id"] == "msn"
    assert data["targets"][0]["requested_action"] == "manual_scroll_observation"
    assert data["live_network_request_performed"] is False
    assert data["browser_automation_performed"] is False
    assert data["screenshot_capture_performed"] is False
    assert data["archive_submission_performed"] is False
    assert data["media_download_performed"] is False
    assert data["credential_value_read"] is False
    assert data["completed_capture_claimed"] is False
    assert "automatic_browser_automation" in data["disallowed_automatic_actions"]
    payload = capture_manual_live_smoke_approval_packet_to_json(packet)
    assert "MANUAL_OPERATOR_ONLY" in payload
    assert "C:" not in payload


def test_packet_rejects_secret_like_input() -> None:
    try:
        build_capture_manual_live_smoke_approval_packet(
            [
                {
                    "site_id": "example",
                    "requested_action": "manual_archive_check",
                    "api_key": "not-allowed",
                }
            ]
        )
    except ValueError as exc:
        assert "secret-like field" in str(exc)
    else:
        raise AssertionError("expected secret-like target metadata to be rejected")


def test_packet_requires_named_targets() -> None:
    try:
        build_capture_manual_live_smoke_approval_packet([])
    except ValueError as exc:
        assert "at least one" in str(exc)
    else:
        raise AssertionError("expected empty target list to be rejected")


if __name__ == "__main__":
    test_packet_is_metadata_only_and_review_gated()
    test_packet_rejects_secret_like_input()
    test_packet_requires_named_targets()
    print("Manual live smoke approval packet self-test passed.")
