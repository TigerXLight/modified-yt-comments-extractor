from __future__ import annotations

import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from capture_manual_live_smoke_observation_packet_store_cli import (
    run_capture_manual_live_smoke_observation_packet_store_cli,
)
from capture_manual_live_smoke_observation_packet_verifier import (
    verify_capture_manual_live_smoke_observation_packet,
)

_GOOD_HASH = "d" * 64


def _cli_payload() -> dict:
    with TemporaryDirectory() as directory:
        observations_path = Path(directory) / "observations.json"
        observations_path.write_text(
            json.dumps(
                [
                    {
                        "site_id": "msn-news",
                        "display_name": "MSN News",
                        "requested_action": "manual comments observation",
                        "operator_summary": "Safe operator note only.",
                        "observed_artifacts": [
                            {
                                "file_name": "msn-note.json",
                                "sha256": _GOOD_HASH,
                                "byte_count": 11,
                                "role": "operator_note_metadata",
                            }
                        ],
                    }
                ]
            ),
            encoding="utf-8",
        )
        stdout = StringIO()
        with redirect_stdout(stdout):
            run_capture_manual_live_smoke_observation_packet_store_cli(
                ["--observations-json", str(observations_path), "--output-directory", str(Path(directory) / "out")]
            )
        return json.loads(stdout.getvalue())


def test_observation_packet_verifier_accepts_safe_cli_payload() -> None:
    report = verify_capture_manual_live_smoke_observation_packet(_cli_payload())
    data = report.to_dict()
    assert data["schema_version"] == "capture_manual_live_smoke_observation_packet_verifier_v1"
    assert data["observation_packet_ready_for_review"] is True
    assert data["issue_count"] == 0
    assert "capture_manual_live_smoke_observation_packet_v1" in data["observed_schema_versions"]
    assert "capture_manual_live_smoke_observation_packet_store_cli_v1" in data["observed_schema_versions"]
    assert data["observed_site_actions"] == ["msn-news:manual comments observation"]
    assert data["live_network_request_performed_by_tool"] is False
    assert data["completed_capture_claimed"] is False


def test_observation_packet_verifier_rejects_unsafe_flags() -> None:
    payload = _cli_payload()
    payload["completed_capture_claimed"] = True
    report = verify_capture_manual_live_smoke_observation_packet(payload)
    assert report.observation_packet_ready_for_review is False
    assert any(issue.code == "unsafe_completed_capture_claimed" for issue in report.issues)


if __name__ == "__main__":
    test_observation_packet_verifier_accepts_safe_cli_payload()
    test_observation_packet_verifier_rejects_unsafe_flags()
    print("Manual live smoke observation packet verifier self-test passed.")
