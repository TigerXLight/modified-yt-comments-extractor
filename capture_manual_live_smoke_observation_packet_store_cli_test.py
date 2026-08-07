from __future__ import annotations

import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from capture_manual_live_smoke_observation_packet_store_cli import (
    run_capture_manual_live_smoke_observation_packet_store_cli,
)

_GOOD_HASH = "c" * 64


def test_observation_packet_store_cli_outputs_safe_json() -> None:
    with TemporaryDirectory() as directory:
        observations_path = Path(directory) / "observations.json"
        output_dir = Path(directory) / "out"
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
            exit_code = run_capture_manual_live_smoke_observation_packet_store_cli(
                [
                    "--observations-json",
                    str(observations_path),
                    "--output-directory",
                    str(output_dir),
                    "--packet-id",
                    "msn-observation-cli",
                ]
            )
        assert exit_code == 0
        data = json.loads(stdout.getvalue())
        assert data["schema_version"] == "capture_manual_live_smoke_observation_packet_store_cli_v1"
        assert data["packet"]["observation_count"] == 1
        assert data["store_result"]["files"][0]["file_name"] == "capture_manual_live_smoke_observation_packet.json"
        assert data["live_network_request_performed_by_tool"] is False
        assert data["completed_capture_claimed"] is False
        rendered = stdout.getvalue()
        assert str(output_dir) not in rendered
        assert str(observations_path) not in rendered


if __name__ == "__main__":
    test_observation_packet_store_cli_outputs_safe_json()
    print("Manual live smoke observation packet store CLI self-test passed.")
