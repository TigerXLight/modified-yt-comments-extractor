from __future__ import annotations

import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from capture_manual_live_smoke_observation_packet_store_cli import (
    run_capture_manual_live_smoke_observation_packet_store_cli,
)
from capture_manual_live_smoke_observation_section_closeout import (
    build_capture_manual_live_smoke_observation_section_closeout_report,
    capture_manual_live_smoke_observation_section_closeout_report_to_json,
)

_GOOD_HASH = "e" * 64


def _cli_payload() -> dict:
    with TemporaryDirectory() as directory:
        observations_path = Path(directory) / "observations.json"
        observations_path.write_text(
            json.dumps(
                {
                    "observations": [
                        {
                            "site_id": "telegraph-news",
                            "display_name": "Telegraph News",
                            "requested_action": "manual article observation",
                            "operator_summary": "Safe operator note only.",
                            "observed_artifacts": [
                                {
                                    "file_name": "telegraph-note.json",
                                    "sha256": _GOOD_HASH,
                                    "byte_count": 12,
                                    "role": "operator_note_metadata",
                                }
                            ],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        stdout = StringIO()
        with redirect_stdout(stdout):
            run_capture_manual_live_smoke_observation_packet_store_cli(
                ["--observations-json", str(observations_path), "--output-directory", str(Path(directory) / "out")]
            )
        return json.loads(stdout.getvalue())


def test_observation_section_closeout_is_review_ready_without_capture_claims() -> None:
    report = build_capture_manual_live_smoke_observation_section_closeout_report(_cli_payload())
    data = report.to_dict()
    assert data["schema_version"] == "capture_manual_live_smoke_observation_section_closeout_v1"
    assert data["roadmap_section"] == "REV4 manual live site-smoke observation intake boundary"
    assert data["section_ready_for_review"] is True
    assert data["issue_count"] == 0
    assert data["completed_capture_claimed"] is False
    rendered = capture_manual_live_smoke_observation_section_closeout_report_to_json(report)
    assert "telegraph-news:manual article observation" in rendered
    assert "No live" not in rendered


if __name__ == "__main__":
    test_observation_section_closeout_is_review_ready_without_capture_claims()
    print("Manual live smoke observation section closeout self-test passed.")
