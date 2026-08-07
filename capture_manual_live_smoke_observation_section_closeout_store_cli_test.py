from __future__ import annotations

import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from capture_manual_live_smoke_observation_packet_store_cli import (
    run_capture_manual_live_smoke_observation_packet_store_cli,
)
from capture_manual_live_smoke_observation_section_closeout_store_cli import (
    run_capture_manual_live_smoke_observation_section_closeout_store_cli,
)

_GOOD_HASH = "1" * 64


def _write_cli_payload(directory: str) -> Path:
    base = Path(directory)
    observations_path = base / "observations.json"
    observations_path.write_text(
        json.dumps(
            [
                {
                    "site_id": "telegraph-news",
                    "display_name": "Telegraph News",
                    "requested_action": "manual article observation",
                    "operator_summary": "Safe operator note only.",
                    "observed_artifacts": [
                        {
                            "file_name": "telegraph-note.json",
                            "sha256": _GOOD_HASH,
                            "byte_count": 22,
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
            ["--observations-json", str(observations_path), "--output-directory", str(base / "packet")]
        )
    payload_path = base / "packet_cli_result.json"
    payload_path.write_text(stdout.getvalue(), encoding="utf-8")
    return payload_path


def test_observation_section_closeout_store_cli_outputs_safe_json() -> None:
    with TemporaryDirectory() as directory:
        payload_path = _write_cli_payload(directory)
        output_dir = Path(directory) / "closeout"
        stdout = StringIO()
        with redirect_stdout(stdout):
            exit_code = run_capture_manual_live_smoke_observation_section_closeout_store_cli(
                ["--artifact-json", str(payload_path), "--output-directory", str(output_dir)]
            )
        assert exit_code == 0
        data = json.loads(stdout.getvalue())
        assert data["schema_version"] == "capture_manual_live_smoke_observation_section_closeout_store_cli_v1"
        assert data["closeout_report"]["section_ready_for_review"] is True
        assert data["store_result"]["files"][0]["file_name"] == "capture_manual_live_smoke_observation_section_closeout.json"
        assert data["live_network_request_performed_by_tool"] is False
        assert data["completed_capture_claimed"] is False
        rendered = stdout.getvalue()
        assert str(output_dir) not in rendered
        assert str(payload_path) not in rendered


if __name__ == "__main__":
    test_observation_section_closeout_store_cli_outputs_safe_json()
    print("Manual live smoke observation section closeout store CLI self-test passed.")
